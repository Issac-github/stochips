package runner

import (
	"reflect"
	"testing"
)

func TestBuildPythonCommandForFetch(t *testing.T) {
	runner := PythonRunner{Python: "python3", AgentDir: "/repo/agent"}

	cmd, args, err := runner.Command("fetch", map[string]string{"date": "20260521"})
	if err != nil {
		t.Fatalf("command: %v", err)
	}

	if cmd != "python3" {
		t.Fatalf("expected python3, got %q", cmd)
	}

	want := []string{"/repo/agent/main.py", "fetch", "20260521"}
	if !reflect.DeepEqual(args, want) {
		t.Fatalf("expected args %v, got %v", want, args)
	}
}

func TestBuildPythonCommandForAgentRun(t *testing.T) {
	runner := PythonRunner{Python: "python", AgentDir: "/repo/agent"}

	_, args, err := runner.Command("agent_run", map[string]string{
		"goal": "完成每日风险巡检",
		"date": "2026-05-21",
	})
	if err != nil {
		t.Fatalf("command: %v", err)
	}

	want := []string{"/repo/agent/main.py", "agent", "完成每日风险巡检", "2026-05-21"}
	if !reflect.DeepEqual(args, want) {
		t.Fatalf("expected args %v, got %v", want, args)
	}
}

func TestBuildPythonCommandRejectsUnknownTask(t *testing.T) {
	runner := PythonRunner{Python: "python", AgentDir: "/repo/agent"}

	_, _, err := runner.Command("unknown", nil)
	if err == nil {
		t.Fatal("expected error")
	}
}
