import { Pool } from "@neondatabase/serverless";

const connectionString = process.env.DATABASE_URL!;

export const pool = new Pool({ connectionString });
