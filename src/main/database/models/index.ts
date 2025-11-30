import Database from 'better-sqlite3'
import { resolve } from 'path'
import path from 'path'
import initArticleTable from './article'
import initEmLimitUpTable from './emLimitUp'
import initHrLimitUpTable from './hrLimitUp'

const db: Database.Database = new Database(
  import.meta.env.MODE !== 'development'
    ? path.join(process.resourcesPath, './storage/sqlite.db')
    : resolve('./storage/sqlite.db')
)
db.pragma('journal_mode = WAL')

initEmLimitUpTable(db)
initHrLimitUpTable(db)
initArticleTable(db)

export default db
