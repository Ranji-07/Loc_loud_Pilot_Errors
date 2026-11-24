import * as vscode from "vscode";
import { createClient, loopbackUrl } from "../../../packages/api-client/src/index";

export * from "../../../packages/api-client/src/index";
export function serverUrl() {
  return loopbackUrl(vscode.workspace.getConfiguration("localpilot").get<string>("serverUrl", "http://127.0.0.1:8765"));
}
export const client = createClient({ baseUrl: serverUrl, surface: "vscode" });
