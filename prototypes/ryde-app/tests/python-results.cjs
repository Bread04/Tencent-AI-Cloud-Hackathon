// Test-only bridge for server-produced public workflow results and legacy migration.
// The browser never imports this helper or executes Python through a subprocess.
const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const python=process.env.PYTHON||[path.join(root,'.venv/Scripts/python.exe'),path.join(root,'.venv/bin/python')].find(file=>fs.existsSync(file))||(process.platform==='win32'?'python':'python3');
const program='import json,sys\nfrom src.agents.rider import run\ntry:\n data=json.load(sys.stdin); result=run(report=data["report"],rider_id=data.get("riderId")); print(json.dumps({"result":result},ensure_ascii=True))\nexcept ValueError as e:\n print(json.dumps({"error":str(e)}))';
const fixtures=new Map();
function run(options){const key=JSON.stringify(options);if(!fixtures.has(key)){const result=JSON.parse(execFileSync(python,['-c',program],{cwd:root,input:key,encoding:'utf8',timeout:15000}));if(result.error)throw new Error(result.error);fixtures.set(key,result.result);}return JSON.parse(JSON.stringify(fixtures.get(key)));}
module.exports={run};
