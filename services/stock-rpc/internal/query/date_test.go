package query

import "testing"

func TestNormalizeDateAcceptsCompactAndDashedDates(t *testing.T) {
	tests := map[string]string{
		"20260522":   "2026-05-22",
		"2026-05-22": "2026-05-22",
	}

	for input, want := range tests {
		got, err := normalizeDate(input)
		if err != nil {
			t.Fatalf("normalizeDate(%q): %v", input, err)
		}
		if got != want {
			t.Fatalf("normalizeDate(%q) = %q, want %q", input, got, want)
		}
	}
}

func TestNormalizeDateRejectsInvalidDate(t *testing.T) {
	if _, err := normalizeDate("20261340"); err == nil {
		t.Fatal("expected invalid date error")
	}
}
