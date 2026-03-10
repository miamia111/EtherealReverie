const canvas = document.getElementById("silk-bg");
const gl = canvas.getContext("webgl");

function resize(){
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;
gl.viewport(0,0,canvas.width,canvas.height);
}

window.addEventListener("resize",resize);
resize();

const vertex = `
attribute vec2 position;
void main(){
gl_Position = vec4(position,0.0,1.0);
}
`;

const fragment = `
precision mediump float;

uniform float time;
uniform vec2 resolution;

float random(vec2 st){
return fract(sin(dot(st.xy,vec2(12.9898,78.233)))*43758.5453123);
}

float noise(vec2 st){
vec2 i=floor(st);
vec2 f=fract(st);

float a=random(i);
float b=random(i+vec2(1.0,0.0));
float c=random(i+vec2(0.0,1.0));
float d=random(i+vec2(1.0,1.0));

vec2 u=f*f*(3.0-2.0*f);

return mix(a,b,u.x)+
(c-a)*u.y*(1.0-u.x)+
(d-b)*u.x*u.y;
}

void main(){

vec2 st=gl_FragCoord.xy/resolution.xy;
st*=2.5;

float t=time*0.35;

float n=noise(st+vec2(t,t));
float n2=noise(st*1.5-vec2(t*0.7,t*0.3));

float mixv=(n+n2)*0.5;

vec3 color1=vec3(0.09,0.05,0.20);
vec3 color2=vec3(0.19,0.10,0.28);

vec3 base=mix(color1,color2,mixv);

/* 增加丝绸亮度层 */

float highlight=pow(mixv,2.0)*0.2;

vec3 color=base+highlight;

gl_FragColor=vec4(color,1.0);
}
`;

function compile(type,source){
const shader=gl.createShader(type);
gl.shaderSource(shader,source);
gl.compileShader(shader);
return shader;
}

const program=gl.createProgram();
gl.attachShader(program,compile(gl.VERTEX_SHADER,vertex));
gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragment));
gl.linkProgram(program);
gl.useProgram(program);

const buffer=gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([
-1,-1,
1,-1,
-1,1,
-1,1,
1,-1,
1,1
]),gl.STATIC_DRAW);

const position=gl.getAttribLocation(program,"position");
gl.enableVertexAttribArray(position);
gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);

const timeLoc=gl.getUniformLocation(program,"time");
const resLoc=gl.getUniformLocation(program,"resolution");

function render(t){
gl.uniform1f(timeLoc,t*0.001);
gl.uniform2f(resLoc,canvas.width,canvas.height);

gl.drawArrays(gl.TRIANGLES,0,6);

requestAnimationFrame(render);
}

requestAnimationFrame(render);