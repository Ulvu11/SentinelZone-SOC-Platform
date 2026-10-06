import "server-only";
import { createApi } from "./api-factory";
import { readData } from "./sentinelzone-data";
export const api = createApi(readData);
