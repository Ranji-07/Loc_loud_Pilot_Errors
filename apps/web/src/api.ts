export * from "../../../packages/api-client/src/index";
import { createClient } from "../../../packages/api-client/src/index";
export const { api, agents, workspace } = createClient();
