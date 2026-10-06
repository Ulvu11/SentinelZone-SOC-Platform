import { readData } from "@/lib/sentinelzone-data";
import { BackendError } from "@/lib/sentinelzone-backend";
export const runtime="nodejs";
export const dynamic="force-dynamic";
async function handle(request:Request,context:{params:Promise<{path:string[]}>}) {
  const headers={"Cache-Control":"no-store, max-age=0"};
  try {
    const {path}=await context.params; const route=path.join("/");
    if(request.method==="POST"&&!['ai/analyze','threat-hunting/search'].includes(route))return Response.json({status:"not_found"},{status:404,headers});
    if(request.method==="POST"&&request.headers.get("origin")!==new URL(request.url).origin)return Response.json({status:"invalid_origin"},{status:403,headers});
    if(Number(request.headers.get("content-length"))>8192)return Response.json({status:"too_large"},{status:413,headers});
    const body=request.method==="POST"?await request.json():undefined;
    return Response.json(await readData(route+new URL(request.url).search,body),{headers});
  }catch(e){return Response.json({status:e instanceof BackendError?e.code:"unavailable"},{status:e instanceof BackendError?e.status:503,headers});}
}
export const GET=handle;
export const POST=handle;
