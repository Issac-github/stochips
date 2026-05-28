import * as protobuf from 'protobufjs'
import * as grpc from '@grpc/grpc-js'

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

const METHODS = {
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
} as const satisfies Record<string, RpcMethod>

export type StockRpcMethod = keyof typeof METHODS

const normalizeTarget = (target: string) => {
  if (target.startsWith(':')) {
    return `localhost${target}`
  }
  return target
}

const getTarget = () =>
  normalizeTarget(process.env.STOCK_RPC_ADDR || 'localhost:50051')

const DEFAULT_DEADLINE_MS = 60_000
const getDeadlineMs = () => {
  const raw = process.env.STOCK_RPC_DEADLINE_MS
  if (!raw) return DEFAULT_DEADLINE_MS
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_DEADLINE_MS
}

const protoRoot = protobuf.parse(STOCK_PROTO).root

let cachedClient: grpc.Client | null = null
let cachedTarget = ''

const getClient = (): grpc.Client => {
  const target = getTarget()
  if (cachedClient && cachedTarget === target) {
    return cachedClient
  }
  if (cachedClient) {
    cachedClient.close()
  }
  // TLS support is opt-in via STOCK_RPC_TLS=1; default to insecure for local dev.
  const credentials =
    process.env.STOCK_RPC_TLS === '1'
      ? grpc.credentials.createSsl()
      : grpc.credentials.createInsecure()
  cachedClient = new grpc.Client(target, credentials, {
    'grpc.keepalive_time_ms': 30_000,
    'grpc.keepalive_timeout_ms': 10_000,
    'grpc.keepalive_permit_without_calls': 1,
    'grpc.max_receive_message_length': 32 * 1024 * 1024
  })
  cachedTarget = target
  return cachedClient
}

export const closeStockRpcClient = () => {
  if (cachedClient) {
    cachedClient.close()
    cachedClient = null
    cachedTarget = ''
  }
}

const buildRequestObject = (payload: RpcPayload): Record<string, unknown> => {
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(payload)) {
    if (value === undefined) continue
    out[key] = value
  }
  // Allow callers to pass camelCase that maps onto snake_case proto fields.
  if (payload.startDate !== undefined) out.start_date = payload.startDate
  if (payload.endDate !== undefined) out.end_date = payload.endDate
  if (payload.taskId !== undefined) out.task_id = payload.taskId
  return out
}

export const callStockRpc = async (
  methodName: StockRpcMethod,
  payload: RpcPayload
): Promise<Record<string, unknown>> => {
  const method = METHODS[methodName]
  if (!method) {
    throw new Error(`Unsupported stock_rpc method: ${methodName}`)
  }

  const requestType = protoRoot.lookupType(method.requestType)
  const responseType = protoRoot.lookupType(method.responseType)

  const requestMessage = requestType.create(buildRequestObject(payload))
  const verifyError = requestType.verify(requestMessage)
  if (verifyError) {
    throw new Error(`Invalid ${method.requestType}: ${verifyError}`)
  }

  const serialize = (value: unknown): Buffer =>
    Buffer.from(requestType.encode(value as protobuf.Message).finish())
  const deserialize = (buffer: Buffer): Record<string, unknown> =>
    responseType.toObject(responseType.decode(buffer), { defaults: true })

  const client = getClient()
  const deadline = Date.now() + getDeadlineMs()

  return new Promise((resolve, reject) => {
    client.makeUnaryRequest(
      method.path,
      serialize,
      deserialize,
      requestMessage,
      new grpc.Metadata(),
      { deadline },
      (error, value) => {
        if (error) {
          reject(error)
          return
        }
        resolve(value ?? {})
      }
    )
  })
}
