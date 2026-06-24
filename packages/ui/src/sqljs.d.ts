declare module "sql.js" {
  interface SqlJsStatic {
    Database: new (data?: ArrayLike<number>) => Database;
  }
  interface Database {
    run(sql: string, params?: any[]): void;
    exec(sql: string, params?: any[]): QueryExecResult[];
    prepare(sql: string, params?: any[]): Statement;
    export(): Uint8Array;
    close(): void;
  }
  interface Statement {
    step(): boolean;
    getAsObject(): Record<string, any>;
    free(): void;
  }
  interface QueryExecResult {
    columns: string[];
    values: any[][];
  }
  function initSqlJs(config?: { locateFile?: (file: string) => string }): Promise<SqlJsStatic>;
  export = initSqlJs;
}
