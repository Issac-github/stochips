package query

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

type Repository struct {
	db *sql.DB
}

func NewRepository(databaseURL string) (*Repository, error) {
	dsn, err := MySQLURLToDSN(databaseURL)
	if err != nil {
		return nil, err
	}
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(8)
	db.SetMaxIdleConns(4)
	db.SetConnMaxLifetime(30 * time.Minute)
	return &Repository{db: db}, nil
}

func (r *Repository) Close() error {
	if r == nil || r.db == nil {
		return nil
	}
	return r.db.Close()
}

func (r *Repository) QueryHrLimitUpJSON(ctx context.Context, startDate string, endDate string) (string, error) {
	start, end, err := normalizeRange(startDate, endDate)
	if err != nil {
		return "", err
	}

	rows, err := r.db.QueryContext(ctx, `
		SELECT
			p.id,
			DATE_FORMAT(p.date, '%Y%m%d') AS qdate,
			p.code,
			p.name,
			COALESCE(p.limit_up_type, '') AS limit_up_type,
			COALESCE(p.open_count, 0) AS open_num,
			COALESCE(p.limit_up_time, '') AS first_limit_up_time,
			COALESCE(p.last_time, p.limit_up_time, '') AS last_limit_up_time,
			COALESCE(p.change_percent, 0) AS change_rate,
			COALESCE(p.turnover_rate, 0) AS turnover_rate,
			COALESCE(p.reason, p.concept, '') AS reason_type,
			COALESCE(p.board_amount, 0) AS order_amount,
			COALESCE(p.volume_ratio, 0) AS limit_up_suc_rate,
			COALESCE(p.market_value, 0) AS currency_value,
			COALESCE(p.latest_price, 0) AS latest,
			COALESCE(p.volume_ratio, 0) AS order_volume,
			COALESCE(c.continuous_days, 1) AS high_days_value
		FROM limit_up_pool p
		LEFT JOIN continuous_limit_up c
			ON c.date = p.date AND c.code = p.code
		WHERE p.date BETWEEN ? AND ?
		ORDER BY p.date DESC, high_days_value DESC, p.limit_up_time ASC, p.code ASC
	`, start, end)
	if err != nil {
		return "", err
	}
	defer rows.Close()

	items := make([]map[string]any, 0)
	for rows.Next() {
		var (
			id             int64
			qdate          string
			code           string
			name           string
			limitUpType    string
			openNum        int
			firstLimitTime string
			lastLimitTime  string
			changeRate     float64
			turnoverRate   float64
			reasonType     string
			orderAmount    float64
			limitUpSucRate float64
			currencyValue  float64
			latest         float64
			orderVolume    float64
			highDaysValue  int
		)
		if err := rows.Scan(
			&id,
			&qdate,
			&code,
			&name,
			&limitUpType,
			&openNum,
			&firstLimitTime,
			&lastLimitTime,
			&changeRate,
			&turnoverRate,
			&reasonType,
			&orderAmount,
			&limitUpSucRate,
			&currencyValue,
			&latest,
			&orderVolume,
			&highDaysValue,
		); err != nil {
			return "", err
		}

		items = append(items, map[string]any{
			"id":                  id,
			"date":                qdate,
			"open_num":            openNum,
			"first_limit_up_time": secondsLike(firstLimitTime),
			"last_limit_up_time":  secondsLike(lastLimitTime),
			"code":                code,
			"limit_up_type":       limitUpType,
			"order_volume":        orderVolume,
			"is_new":              0,
			"limit_up_suc_rate":   limitUpSucRate,
			"currency_value":      currencyValue * 100000000,
			"market_id":           marketID(code),
			"is_again_limit":      boolInt(highDaysValue > 1),
			"change_rate":         changeRate,
			"turnover_rate":       turnoverRate,
			"reason_type":         reasonType,
			"order_amount":        orderAmount,
			"high_days":           fmt.Sprintf("%d连板", highDaysValue),
			"name":                name,
			"high_days_value":     highDaysValue,
			"change_tag":          "",
			"market_type":         marketType(code),
			"latest":              latest,
			"time_preview":        []int{},
		})
	}
	if err := rows.Err(); err != nil {
		return "", err
	}
	return marshal(items)
}

func (r *Repository) QueryEmLimitUpJSON(ctx context.Context, startDate string, endDate string) (string, error) {
	start, end, err := normalizeRange(startDate, endDate)
	if err != nil {
		return "", err
	}

	rows, err := r.db.QueryContext(ctx, `
		SELECT
			id,
			DATE_FORMAT(date, '%Y%m%d') AS qdate,
			code,
			name,
			COALESCE(latest_price, 0) AS latest_price,
			COALESCE(change_percent, 0) AS change_percent,
			COALESCE(turnover, 0) AS turnover,
			COALESCE(circulating_value, market_value, 0) AS circulating_value,
			COALESCE(market_value, 0) AS market_value,
			COALESCE(turnover_rate, 0) AS turnover_rate,
			COALESCE(limit_up_type, '') AS limit_up_type,
			COALESCE(first_limit_up_time, '') AS first_limit_up_time,
			COALESCE(last_limit_up_time, '') AS last_limit_up_time,
			COALESCE(board_amount, 0) AS board_amount,
			COALESCE(block_name, '') AS block_name,
			COALESCE(reason, '') AS reason
		FROM eastmoney_zt_pool
		WHERE date BETWEEN ? AND ?
		ORDER BY date DESC, first_limit_up_time ASC, code ASC
	`, start, end)
	if err != nil {
		return "", err
	}
	defer rows.Close()

	items := make([]map[string]any, 0)
	for rows.Next() {
		var (
			id               int64
			qdate            string
			code             string
			name             string
			latestPrice      float64
			changePercent    float64
			turnover         int64
			circulatingValue float64
			marketValue      float64
			turnoverRate     float64
			limitUpType      string
			firstLimitTime   string
			lastLimitTime    string
			boardAmount      float64
			blockName        string
			reason           string
		)
		if err := rows.Scan(
			&id,
			&qdate,
			&code,
			&name,
			&latestPrice,
			&changePercent,
			&turnover,
			&circulatingValue,
			&marketValue,
			&turnoverRate,
			&limitUpType,
			&firstLimitTime,
			&lastLimitTime,
			&boardAmount,
			&blockName,
			&reason,
		); err != nil {
			return "", err
		}

		lbc := limitBoardCount(limitUpType)
		items = append(items, map[string]any{
			"id":         id,
			"c":          code,
			"qdate":      atoiDefault(qdate, 0),
			"m":          marketID(code),
			"n":          name,
			"p":          latestPrice * 1000,
			"zdp":        changePercent,
			"amount":     turnover,
			"ltsz":       circulatingValue * 100000 * 1000,
			"tshare":     marketValue * 100000 * 1000,
			"hs":         turnoverRate,
			"lbc":        lbc,
			"fbt":        timeNumber(firstLimitTime),
			"lbt":        timeNumber(lastLimitTime),
			"fund":       boardAmount,
			"zbc":        0,
			"hybk":       firstNonEmpty(blockName, reason),
			"zttj":       []map[string]int{{"days": maxInt(lbc, 1), "ct": 1}},
			"created_at": "",
			"updated_at": "",
		})
	}
	if err := rows.Err(); err != nil {
		return "", err
	}
	return marshal(items)
}

func (r *Repository) QueryBrokenBoardJSON(ctx context.Context, startDate string, endDate string) (string, error) {
	hrJSON, err := r.QueryHrLimitUpJSON(ctx, startDate, endDate)
	if err != nil {
		return "", err
	}
	var hrItems []map[string]any
	if err := json.Unmarshal([]byte(hrJSON), &hrItems); err != nil {
		return "", err
	}

	dateSet := map[string]bool{}
	stockData := map[string][]map[string]any{}
	for _, item := range hrItems {
		date, _ := item["date"].(string)
		code, _ := item["code"].(string)
		if date == "" || code == "" {
			continue
		}
		dateSet[date] = true
		stockData[code] = append(stockData[code], item)
	}
	dates := sortedKeys(dateSet)
	dateIndex := map[string]int{}
	for i, item := range dates {
		dateIndex[item] = i
	}

	results := make([]map[string]any, 0)
	for code, items := range stockData {
		byDate := map[string]map[string]any{}
		for _, item := range items {
			date, _ := item["date"].(string)
			byDate[date] = item
		}
		for i, currentDate := range dates {
			currentData := byDate[currentDate]
			if currentData == nil {
				continue
			}
			var firstDate string
			var firstData map[string]any
			for j := i - 1; j >= 0 && j >= i-5; j-- {
				if data := byDate[dates[j]]; data != nil {
					firstDate = dates[j]
					firstData = data
					break
				}
			}
			if firstData == nil {
				continue
			}
			firstIndex := dateIndex[firstDate]
			var brokenDate string
			for k := firstIndex + 1; k < i; k++ {
				if byDate[dates[k]] == nil {
					brokenDate = dates[k]
					break
				}
			}
			if brokenDate == "" {
				continue
			}
			name, _ := currentData["name"].(string)
			results = append(results, map[string]any{
				"code":              code,
				"name":              name,
				"firstLimitUpDate":  firstDate,
				"brokenDate":        brokenDate,
				"secondLimitUpDate": currentDate,
				"firstLimitUpData":  firstData,
				"secondLimitUpData": currentData,
				"daysBetween":       i - firstIndex,
			})
		}
	}
	return marshal(results)
}

func normalizeRange(startDate string, endDate string) (string, string, error) {
	start, err := normalizeDate(startDate)
	if err != nil {
		return "", "", fmt.Errorf("invalid start_date: %w", err)
	}
	end, err := normalizeDate(endDate)
	if err != nil {
		return "", "", fmt.Errorf("invalid end_date: %w", err)
	}
	return start, end, nil
}

func normalizeDate(value string) (string, error) {
	value = strings.TrimSpace(value)
	for _, layout := range []string{"20060102", "2006-01-02"} {
		parsed, err := time.Parse(layout, value)
		if err == nil {
			return parsed.Format("2006-01-02"), nil
		}
	}
	return "", fmt.Errorf("unsupported date %q", value)
}

func marshal(value any) (string, error) {
	data, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// MySQLURLToDSN converts a "mysql+pymysql://..." URL (as used in Python config)
// into the DSN format expected by go-sql-driver/mysql.
func MySQLURLToDSN(databaseURL string) (string, error) {
	const prefix = "mysql+pymysql://"
	if !strings.HasPrefix(databaseURL, prefix) {
		return "", fmt.Errorf("unsupported DATABASE_URL, expected %s", prefix)
	}
	raw := strings.TrimPrefix(databaseURL, prefix)
	parts := strings.SplitN(raw, "@", 2)
	if len(parts) != 2 {
		return "", fmt.Errorf("invalid DATABASE_URL")
	}
	userPass := parts[0]
	hostDB := parts[1]

	credentials := strings.SplitN(userPass, ":", 2)
	if len(credentials) != 2 {
		return "", fmt.Errorf("invalid DATABASE_URL credentials")
	}

	pathParts := strings.SplitN(hostDB, "/", 2)
	if len(pathParts) != 2 {
		return "", fmt.Errorf("invalid DATABASE_URL database")
	}

	host := pathParts[0]
	databaseAndQuery := pathParts[1]
	database := databaseAndQuery
	query := "parseTime=true&charset=utf8mb4"
	if strings.Contains(databaseAndQuery, "?") {
		dbParts := strings.SplitN(databaseAndQuery, "?", 2)
		database = dbParts[0]
		query = dbParts[1] + "&parseTime=true"
	}

	return fmt.Sprintf("%s:%s@tcp(%s)/%s?%s", credentials[0], credentials[1], host, database, query), nil
}

func marketType(code string) string {
	switch {
	case strings.HasPrefix(code, "688"):
		return "STAR"
	case strings.HasPrefix(code, "300"), strings.HasPrefix(code, "301"):
		return "GEM"
	default:
		return "HS"
	}
}

func marketID(code string) int {
	if strings.HasPrefix(code, "6") {
		return 1
	}
	return 0
}

func boolInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

func secondsLike(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return "0"
	}
	if _, err := strconv.Atoi(value); err == nil {
		return value
	}
	parsed, err := time.Parse("15:04:05", value)
	if err != nil {
		return "0"
	}
	return strconv.Itoa(parsed.Hour()*3600 + parsed.Minute()*60 + parsed.Second())
}

func timeNumber(value string) int {
	value = strings.TrimSpace(value)
	if value == "" {
		return 0
	}
	digits := strings.NewReplacer(":", "", "-", "", " ", "").Replace(value)
	return atoiDefault(digits, 0)
}

func limitBoardCount(value string) int {
	for _, field := range strings.FieldsFunc(value, func(r rune) bool {
		return r < '0' || r > '9'
	}) {
		if n, err := strconv.Atoi(field); err == nil && n > 0 {
			return n
		}
	}
	if strings.Contains(value, "连") {
		return 2
	}
	return 1
}

func atoiDefault(value string, fallback int) int {
	n, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return n
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func maxInt(a int, b int) int {
	if a > b {
		return a
	}
	return b
}

func sortedKeys(values map[string]bool) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	for i := 0; i < len(keys); i++ {
		for j := i + 1; j < len(keys); j++ {
			if keys[j] < keys[i] {
				keys[i], keys[j] = keys[j], keys[i]
			}
		}
	}
	return keys
}
