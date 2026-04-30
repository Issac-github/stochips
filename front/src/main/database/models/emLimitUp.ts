import Database from 'better-sqlite3'
import { debugLog, errorLog } from '@shared/logger'

export const migrateEmLimitUpTable = (db: Database.Database) => {
  try {
    const tableExists = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='emLimitUp'"
      )
      .get()

    if (tableExists) {
      debugLog('Found old table emLimitUp, starting migration...')
      const createNewTableQuery = `
        CREATE TABLE IF NOT EXISTS em_limit_up (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          c TEXT,
          qdate INTEGER,
          m INTEGER,
          n TEXT,
          p INTEGER,
          zdp REAL,
          amount INTEGER,
          ltsz REAL,
          tshare REAL,
          hs REAL,
          lbc INTEGER,
          fbt INTEGER,
          lbt INTEGER,
          fund INTEGER,
          zbc INTEGER,
          hybk TEXT,
          zttj TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (c, qdate)
        )
      `
      db.exec(createNewTableQuery)
      const migrateDataQuery = `
        INSERT OR IGNORE INTO em_limit_up
        SELECT * FROM emLimitUp
      `
      db.exec(migrateDataQuery)
      // db.exec('DROP TABLE emLimitUp')
      debugLog('Migration completed: emLimitUp -> em_limit_up')
    }
  } catch (err) {
    errorLog('Error during migration:', err)
    throw err
  }
}

const initEmLimitUpTable = (db: Database.Database) => {
  try {
    const createTableQuery = `
      CREATE TABLE IF NOT EXISTS em_limit_up (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        c TEXT,
        qdate INTEGER,
        m INTEGER,
        n TEXT,
        p INTEGER,
        zdp REAL,
        amount INTEGER,
        ltsz REAL,
        tshare REAL,
        hs REAL,
        lbc INTEGER,
        fbt INTEGER,
        lbt INTEGER,
        fund INTEGER,
        zbc INTEGER,
        hybk TEXT,
        zttj TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (c, qdate)
      )
    `
    db.exec(createTableQuery)
    debugLog('em_limit_up table initialized successfully')
  } catch (err) {
    errorLog('Error initializing database:', err)
    throw err
  }
}

export default initEmLimitUpTable
