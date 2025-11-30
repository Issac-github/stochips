import Database from 'better-sqlite3'
import { debugLog, errorLog } from '@shared/logger'

export const migrateHrLimitUpTable = (db: Database.Database) => {
  try {
    const tableExists = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='hrLimitUp'"
      )
      .get()
    if (tableExists) {
      debugLog('Found old table hrLimitUp, starting migration...')
      db.exec(`
        CREATE TABLE IF NOT EXISTS hr_limit_up (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date TEXT,
          open_num INTEGER,
          first_limit_up_time TEXT,
          last_limit_up_time TEXT,
          code TEXT,
          limit_up_type TEXT,
          order_volume INTEGER,
          is_new INTEGER,
          limit_up_suc_rate REAL,
          currency_value REAL,
          market_id INTEGER,
          is_again_limit INTEGER,
          change_rate REAL,
          turnover_rate REAL,
          reason_type TEXT,
          order_amount REAL,
          high_days TEXT,
          name TEXT,
          high_days_value INTEGER,
          change_tag TEXT,
          market_type TEXT,
          latest REAL,
          time_preview TEXT,
          UNIQUE(code, date)
        );
      `)
      db.exec(`
        INSERT OR IGNORE INTO hr_limit_up
        SELECT * FROM hrLimitUp
      `)
      // db.exec('DROP TABLE hrLimitUp')
      debugLog('Migration completed: hrLimitUp -> hr_limit_up')
    }
  } catch (err) {
    errorLog('Error during migration:', err)
    throw err
  }
}

const initHrLimitUpTable = (db: Database.Database) => {
  try {
    db.exec(`
      CREATE TABLE IF NOT EXISTS hr_limit_up (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        open_num INTEGER,
        first_limit_up_time TEXT,
        last_limit_up_time TEXT,
        code TEXT,
        limit_up_type TEXT,
        order_volume INTEGER,
        is_new INTEGER,
        limit_up_suc_rate REAL,
        currency_value REAL,
        market_id INTEGER,
        is_again_limit INTEGER,
        change_rate REAL,
        turnover_rate REAL,
        reason_type TEXT,
        order_amount REAL,
        high_days TEXT,
        name TEXT,
        high_days_value INTEGER,
        change_tag TEXT,
        market_type TEXT,
        latest REAL,
        time_preview TEXT,
        UNIQUE(code, date)
      );
    `)
    debugLog('hr_limit_up table initialized successfully')
  } catch (err) {
    errorLog('Error initializing database:', err)
    throw err
  }
}

export default initHrLimitUpTable
