import { ClientHttp2Stream, connect } from 'node:http2'
import * as protobuf from 'protobufjs'

const SERVICE = 'stochips.stock.v1.StockService'

const STOCK_PROTO = `
syntax = "proto3";

package stochips.stock.v1;

service StockService {
  rpc SubmitFetch(FetchRequest) returns (TaskReply);
  rpc SubmitAssess(AssessRequest) returns (TaskReply);
  rpc SubmitAssessAi(AssessAiRequest) returns (TaskReply);
  rpc RunAgent(AgentRequest) returns (TaskReply);
  rpc GetTask(TaskRequest) returns (TaskStatusReply);
  rpc QueryHrLimitUp(QueryRangeRequest) returns (JsonReply);
  rpc QueryEmLimitUp(QueryRangeRequest) returns (JsonReply);
  rpc QueryBrokenBoard(QueryRangeRequest) returns (JsonReply);
}

message FetchRequest {
  string date = 1;
}

message AssessRequest {
  string date = 1;
}

message AssessAiRequest {
  string date = 1;
}

message AgentRequest {
  string goal = 1;
  string date = 2;
}

message TaskReply {
  string task_id = 1;
}

message TaskRequest {
  string task_id = 1;
}

message TaskStatusReply {
  string task_id = 1;
  string type = 2;
  string status = 3;
  string result = 4;
  string error = 5;
}

message QueryRangeRequest {
  string start_date = 1;
  string end_date = 2;
}

message JsonReply {
  string json = 1;
}
`

type RpcPayload = Record<string, string | undefined>

type RpcMethod = {
  path: string
  requestType: string
  responseType: string
}

const METHODS: Record<string, RpcMethod> = {
  SubmitFetch: {
    path: `/${SERVICE}/SubmitFetch`,
    requestType: 'stochips.stock.v1.FetchRequest',
    responseType: 'stochips.stock.v1.TaskReply'
  },
  SubmitAssess: {
    path: `/${SERVICE}/SubmitAssess`,
    requestType: 'stochips.stock.v1.AssessRequest',
    responseType: 'stochips.stock.v1.TaskReply'
  },
  SubmitAssessAi: {
    path: `/${SERVICE}/SubmitAssessAi`,
    requestType: 'stochips.stock.v1.AssessAiRequest',
    responseType: 'stochips.stock.v1.TaskReply'
  },
  RunAgent: {
    path: `/${SERVICE}/RunAgent`,
    requestType: 'stochips.stock.v1.AgentRequest',
    responseType: 'stochips.stock.v1.TaskReply'
  },
  GetTask: {
    path: `/${SERVICE}/GetTask`,
    requestType: 'stochips.stock.v1.TaskRequest',
    responseType: 'stochips.stock.v1.TaskStatusReply'
  },
  QueryHrLimitUp: {
    path: `/${SERVICE}/QueryHrLimitUp`,
    requestType: 'stochips.stock.v1.QueryRangeRequest',
    responseType: 'stochips.stock.v1.JsonReply'
  },
  QueryEmLimitUp: {
    path: `/${SERVICE}/QueryEmLimitUp`,
    requestType: 'stochips.stock.v1.QueryRangeRequest',
    responseType: 'stochips.stock.v1.JsonReply'
  },
  QueryBrokenBoard: {
    path: `/${SERVICE}/QueryBrokenBoard`,
    requestType: 'stochips.stock.v1.QueryRangeRequest',
    responseType: 'stochips.stock.v1.JsonReply'
  }
}

let protoRootPromise: Promise<protobuf.Root> | null = null

const normalizeTarget = (target: string) => {
  if (target.startsWith(':')) {
    return `localhost${target}`
  }
  return target
}

const getTarget = () =>
  normalizeTarget(process.env.STOCK_RPC_ADDR || 'localhost:50051')

const getProtoRoot = () => {
  if (!protoRootPromise) {
    protoRootPromise = Promise.resolve(protobuf.parse(STOCK_PROTO).root)
  }
  return protoRootPromise
}

const encodeFrame = (message: Uint8Array) => {
  const frame = Buffer.alloc(5 + message.length)
  frame.writeUInt8(0, 0)
  frame.writeUInt32BE(message.length, 1)
  Buffer.from(message).copy(frame, 5)
  return frame
}

const decodeFrame = (chunks: Buffer[]) => {
  const body = Buffer.concat(chunks)
  if (body.length < 5) {
    throw new Error('Invalid gRPC response: missing frame header')
  }
  const compressed = body.readUInt8(0)
  if (compressed !== 0) {
    throw new Error('Compressed gRPC responses are not supported')
  }
  const length = body.readUInt32BE(1)
  if (body.length < 5 + length) {
    throw new Error('Invalid gRPC response: incomplete frame')
  }
  return body.subarray(5, 5 + length)
}

const readGrpcStatus = (trailers: Record<string, unknown>) => {
  const status = trailers['grpc-status']
  return Array.isArray(status) ? status[0] : status
}

const readGrpcMessage = (trailers: Record<string, unknown>) => {
  const message = trailers['grpc-message']
  return Array.isArray(message) ? message[0] : message
}

export const callStockRpc = async (
  methodName: keyof typeof METHODS,
  payload: RpcPayload
): Promise<Record<string, unknown>> => {
  const method = METHODS[methodName]
  if (!method) {
    throw new Error(`Unsupported stock_rpc method: ${methodName}`)
  }

  const root = await getProtoRoot()
  const requestType = root.lookupType(method.requestType)
  const responseType = root.lookupType(method.responseType)
  const requestMessage = requestType.create({
    ...payload,
    start_date: payload.startDate,
    end_date: payload.endDate,
    task_id: payload.taskId
  })
  const requestBuffer = requestType.encode(requestMessage).finish()

  return new Promise((resolve, reject) => {
    const session = connect(`http://${getTarget()}`)
    const chunks: Buffer[] = []
    let trailers: Record<string, unknown> = {}

    const closeWithError = (error: Error) => {
      session.close()
      reject(error)
    }

    session.on('error', closeWithError)

    const stream: ClientHttp2Stream = session.request({
      ':method': 'POST',
      ':path': method.path,
      'content-type': 'application/grpc',
      te: 'trailers'
    })

    stream.on('response', (headers) => {
      trailers = { ...trailers, ...headers }
    })
    stream.on('trailers', (headers) => {
      trailers = { ...trailers, ...headers }
    })
    stream.on('data', (chunk: Buffer) => {
      chunks.push(chunk)
    })
    stream.on('error', closeWithError)
    stream.on('end', () => {
      session.close()
      const grpcStatus = readGrpcStatus(trailers)
      if (grpcStatus && grpcStatus !== '0') {
        reject(
          new Error(
            `stock_rpc failed with grpc-status ${grpcStatus}: ${
              readGrpcMessage(trailers) || 'unknown error'
            }`
          )
        )
        return
      }

      try {
        const responseBuffer = decodeFrame(chunks)
        const response = responseType.decode(responseBuffer)
        resolve(responseType.toObject(response, { defaults: true }))
      } catch (error) {
        reject(error)
      }
    })

    stream.end(encodeFrame(requestBuffer))
  })
}
