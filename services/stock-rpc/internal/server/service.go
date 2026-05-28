package server

import (
	"context"

	stockv1 "stochips/stock_rpc/gen/stockv1"
	"stochips/stock_rpc/internal/query"
	"stochips/stock_rpc/internal/tasks"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type Executor interface {
	Run(ctx context.Context, taskType string, request map[string]string) (string, error)
}

type StockService struct {
	stockv1.UnimplementedStockServiceServer

	store    tasks.Store
	executor Executor
	queries  *query.Repository
}

func NewStockService(store tasks.Store, executor Executor, queries *query.Repository) *StockService {
	return &StockService{store: store, executor: executor, queries: queries}
}

func (s *StockService) SubmitFetch(ctx context.Context, req *stockv1.FetchRequest) (*stockv1.TaskReply, error) {
	return s.submit(ctx, "fetch", map[string]string{"date": req.GetDate()})
}

func (s *StockService) SubmitAssess(ctx context.Context, req *stockv1.AssessRequest) (*stockv1.TaskReply, error) {
	return s.submit(ctx, "assess", map[string]string{"date": req.GetDate()})
}

func (s *StockService) SubmitAssessAi(ctx context.Context, req *stockv1.AssessAiRequest) (*stockv1.TaskReply, error) {
	return s.submit(ctx, "assess_ai", map[string]string{"date": req.GetDate()})
}

func (s *StockService) RunAgent(ctx context.Context, req *stockv1.AgentRequest) (*stockv1.TaskReply, error) {
	return s.submit(ctx, "agent_run", map[string]string{
		"goal": req.GetGoal(),
		"date": req.GetDate(),
	})
}

func (s *StockService) GetTask(_ context.Context, req *stockv1.TaskRequest) (*stockv1.TaskStatusReply, error) {
	task, ok := s.store.Get(req.GetTaskId())
	if !ok {
		return nil, status.Errorf(codes.NotFound, "task %q not found", req.GetTaskId())
	}

	return &stockv1.TaskStatusReply{
		TaskId: task.ID,
		Type:   task.Type,
		Status: string(task.Status),
		Result: task.Result,
		Error:  task.Error,
	}, nil
}

func (s *StockService) QueryHrLimitUp(ctx context.Context, req *stockv1.QueryRangeRequest) (*stockv1.JsonReply, error) {
	if s.queries == nil {
		return nil, status.Error(codes.FailedPrecondition, "query repository is not configured")
	}
	result, err := s.queries.QueryHrLimitUpJSON(ctx, req.GetStartDate(), req.GetEndDate())
	if err != nil {
		return nil, status.Error(codes.Internal, err.Error())
	}
	return &stockv1.JsonReply{Json: result}, nil
}

func (s *StockService) QueryEmLimitUp(ctx context.Context, req *stockv1.QueryRangeRequest) (*stockv1.JsonReply, error) {
	if s.queries == nil {
		return nil, status.Error(codes.FailedPrecondition, "query repository is not configured")
	}
	result, err := s.queries.QueryEmLimitUpJSON(ctx, req.GetStartDate(), req.GetEndDate())
	if err != nil {
		return nil, status.Error(codes.Internal, err.Error())
	}
	return &stockv1.JsonReply{Json: result}, nil
}

func (s *StockService) QueryBrokenBoard(ctx context.Context, req *stockv1.QueryRangeRequest) (*stockv1.JsonReply, error) {
	if s.queries == nil {
		return nil, status.Error(codes.FailedPrecondition, "query repository is not configured")
	}
	result, err := s.queries.QueryBrokenBoardJSON(ctx, req.GetStartDate(), req.GetEndDate())
	if err != nil {
		return nil, status.Error(codes.Internal, err.Error())
	}
	return &stockv1.JsonReply{Json: result}, nil
}

func (s *StockService) submit(ctx context.Context, taskType string, request map[string]string) (*stockv1.TaskReply, error) {
	task := s.store.Create(taskType, request)

	go func() {
		runCtx := context.WithoutCancel(ctx)
		if err := s.store.MarkRunning(task.ID); err != nil {
			return
		}

		result, err := s.executor.Run(runCtx, taskType, request)
		if err != nil {
			_ = s.store.MarkFailed(task.ID, err)
			return
		}
		_ = s.store.MarkSucceeded(task.ID, result)
	}()

	return &stockv1.TaskReply{TaskId: task.ID}, nil
}
