#version 440
// Raycasting of an orbital grid, same steps as elucida.core.orbitals.render/_trace (numpy); see elucida/core/gpu3d.py.
// pass 1 = one ray per pixel centre, pass 2 (PASS2) = edge pixels again with 2x2 sub-samples.
// Output: pass 1 premultiplied colour and coverage (RGBA32F), pass 2 straight colour (divided by the coverage).
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    vec4 I0, Ix, Iy, Iz;       // grid index = I0 + X*Ix + Y*Iy + z*Iz (screen X, Y, depth z in A)
    vec4 M0, M1, M2;           // view normal = -(sign) * (g.x*M0 + g.y*M1 + g.z*M2), g = index-space gradient
    vec4 lim;                  // xlim0, ylim0, px, py
    vec4 size;                 // W, H, tile, yup
    vec4 nstep;                // n0, n1, n2, step
    vec4 iso;                  // iso, alpha+, alpha-, zoff
    vec4 cp;                   // colour +, aa
    vec4 cm;                   // colour -, has occ2
    vec4 L0, L1, L2;           // lights: direction, weight
    vec4 reg;                  // exponent, diffuse, gloss, gloss factor
    vec4 fade;                 // fog start, fog length, max layers, AA edge
};
layout(binding = 1) uniform sampler3D vol;     // R32F: width n2, height n1, depth n0
layout(binding = 2) uniform sampler2D tiles;   // RGBA32F: lo, hi, active
layout(binding = 3) uniform sampler2D occ;     // R32F W x H, row 0 = bottom image row
layout(binding = 4) uniform sampler2D occ2;    // R32F 2W x 2H
#ifdef PASS2
layout(binding = 5) uniform sampler2D pre;     // pass 1 result
#endif

float V(ivec3 p) { return texelFetch(vol, ivec3(p.z, p.y, p.x), 0).r; }

bool cell(vec3 I, out ivec3 i0, out vec3 f) {
    vec3 n = nstep.xyz;
    if (any(lessThan(I, vec3(0.0))) || any(greaterThan(I, n - 1.0001))) return false;
    vec3 fl = floor(I);
    i0 = ivec3(fl);
    f = I - fl;
    return true;
}

float sampleV(vec3 I) {
    ivec3 i0; vec3 f;
    if (!cell(I, i0, f)) return 0.0;
    float acc = 0.0;
    for (int c = 0; c < 8; c++) {
        ivec3 o = ivec3((c >> 2) & 1, (c >> 1) & 1, c & 1);
        vec3 w = mix(vec3(1.0) - f, f, vec3(o));
        acc += w.x * w.y * w.z * V(i0 + o);
    }
    return acc;
}

float G(ivec3 p, int a) {                      // np.gradient along index axis a
    ivec3 e = ivec3(0); e[a] = 1;
    int n = int(nstep[a]);
    if (p[a] == 0) return V(p + e) - V(p);
    if (p[a] == n - 1) return V(p) - V(p - e);
    return (V(p + e) - V(p - e)) * 0.5;
}

vec3 sampleG(vec3 I) {
    ivec3 i0; vec3 f;
    if (!cell(I, i0, f)) return vec3(0.0);
    vec3 acc = vec3(0.0);
    for (int c = 0; c < 8; c++) {
        ivec3 o = ivec3((c >> 2) & 1, (c >> 1) & 1, c & 1);
        vec3 w = mix(vec3(1.0) - f, f, vec3(o));
        ivec3 p = i0 + o;
        acc += w.x * w.y * w.z * vec3(G(p, 0), G(p, 1), G(p, 2));
    }
    return acc;
}


vec4 tracePx(float X, float Y, float top, float floorz) {
    float step = nstep.w;
    vec3 base = I0.xyz + X * Ix.xyz + Y * Iy.xyz;
    vec3 colL[4]; float aL[4];
    int m = 0;
    int maxl = int(fade.z);
    float vp = 0.0; vec3 Ip = vec3(0.0); float zp = 0.0;
    for (int j = 0; j < 100000; j++) {
        float z = top - step * float(j);
        bool live = z >= floorz - step;
        vec3 I = base + z * Iz.xyz;
        float v = live ? sampleV(I) : 0.0;
        if (j > 0 && !(abs(vp) > iso.x) && abs(v) > iso.x) {
            float a0 = abs(vp), a1 = abs(v);
            float t = clamp((iso.x - a0) / max(a1 - a0, 1e-12), 0.0, 1.0);
            float zc = zp - t * step;
            if (zc > floorz) {
                vec3 Ic = Ip + t * (I - Ip);
                vec3 g = sampleG(Ic);
                float sg = sign(v);
                vec3 nv = -sg * (g.x * M0.xyz + g.y * M1.xyz + g.z * M2.xyz);
                nv /= max(length(nv), 1e-12);
                float D = 0.0, S = 0.0;
                vec4 Ls[3] = vec4[3](L0, L1, L2);
                for (int k = 0; k < 3; k++) {
                    float c = clamp(dot(nv, Ls[k].xyz), 0.0, 1.0);
                    D += Ls[k].w * reg.y * pow(c, reg.x);
                    S += Ls[k].w * reg.z * (reg.w * pow(c, 16.0) + 1.2 * pow(c, 64.0));
                }
                vec3 bc = sg > 0.0 ? cp.rgb : cm.rgb;
                vec3 col = clamp(bc * D + S, 0.0, 1.0);
                float fog = clamp((-(zc + iso.w) - fade.x) / fade.y, 0.0, 1.0);
                col = col + (1.0 - col) * fog;
                float al = sg > 0.0 ? iso.y : iso.z;
                float a = clamp(al * D / clamp(abs(nv.z), 0.1, 1.0), 0.0, 1.0);
                colL[m % 4] = col; aL[m % 4] = a;   // keep the hindmost max layers (ring)
                m++;
            }
        }
        if (!live) break;
        vp = v; Ip = I; zp = z;
    }
    vec3 Cb = vec3(0.0); float Ab = 0.0;
    int L = min(m, maxl);
    for (int r = 0; r < L; r++) {               // hindmost first
        int k = (m - 1 - r) % 4;
        Cb = colL[k] * aL[k] + Cb * (1.0 - aL[k]);
        Ab = aL[k] + Ab * (1.0 - aL[k]);
    }
    return vec4(Cb, Ab);
}

void main() {
    ivec2 t = ivec2(gl_FragCoord.xy);
    int W = int(size.x), H = int(size.y), TL = int(size.z);
    int ix = t.x;
    int iy = size.w > 0.5 ? t.y : H - 1 - t.y;   // image row, 0 = bottom
    vec4 tl = texelFetch(tiles, ivec2(ix / TL, iy / TL), 0);
#ifndef PASS2
    if (tl.z < 0.5) { fragColor = vec4(0.0); return; }
    float fl = max(texelFetch(occ, ivec2(ix, iy), 0).r, tl.x);
    fragColor = tracePx((float(ix) + 0.5) * lim.z + lim.x, (float(iy) + 0.5) * lim.w + lim.y, tl.y, fl);
#else
    vec4 c0 = texelFetch(pre, t, 0);
    bool edge = false;
    if (cp.w > 0.5 && tl.z > 0.5) {
        ivec2 nb[4] = ivec2[4](ivec2(1, 0), ivec2(-1, 0), ivec2(0, 1), ivec2(0, -1));
        for (int k = 0; k < 4; k++) {
            ivec2 q = t + nb[k];
            if (q.x < 0 || q.y < 0 || q.x >= W || q.y >= H) continue;
            vec4 d = abs(texelFetch(pre, q, 0) - c0);
            if (max(max(d.x, d.y), max(d.z, d.w)) > fade.w) edge = true;
        }
    }
    if (!edge) { fragColor = c0.a > 0.0 ? vec4(c0.rgb / c0.a, c0.a) : vec4(0.0); return; }
    vec4 sub = vec4(0.0);
    for (int s = 0; s < 4; s++) {
        float oy = (s < 2) ? 0.25 : 0.75;
        float ox = (s % 2 == 0) ? 0.25 : 0.75;
        float fl;
        if (cm.w > 0.5)
            fl = max(texelFetch(occ2, ivec2(2 * ix + int(ox > 0.5), 2 * iy + int(oy > 0.5)), 0).r, tl.x);
        else
            fl = max(texelFetch(occ, ivec2(ix, iy), 0).r, tl.x);
        sub += tracePx((float(ix) + ox) * lim.z + lim.x, (float(iy) + oy) * lim.w + lim.y, tl.y, fl) * 0.25;
    }
    fragColor = sub.a > 0.0 ? vec4(sub.rgb / sub.a, sub.a) : vec4(0.0);
#endif
}
