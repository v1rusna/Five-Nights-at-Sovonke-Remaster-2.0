init -1 python in v1FNaSRShaders:

    VHS_CRT_SHADER_NAME = "V1FNaSR.VHS_CRT"

    VHS_CRT_VARIABLES = """
        uniform sampler2D tex0;
        uniform float u_time;

        uniform float u_glitch_speed;
        uniform float u_glitch_power;

        attribute vec2 a_tex_coord;

        varying vec2 v_tex_coord;
    """

    VHS_CRT_VERTEX_300 = """
        v_tex_coord = a_tex_coord;
    """

    VHS_CRT_FRAGMENT_300 = """
        vec2 uv = v_tex_coord;

        float time = mod(u_time * 100.0, 32.0) / u_glitch_speed;

        float GLITCH = u_glitch_power;

        float gnm = sat( GLITCH );
        float rnd0 = rand( mytrunc( vec2(time, time), 6.0 ) );
        float r0 = sat((1.0 - gnm) * 0.7 + rnd0);
        float rnd1 = rand( vec2(mytrunc( uv.x, 10.0 * r0 ), time) );
        float r1 = 0.5 - 0.5 * gnm + rnd1;
        r1 = 1.0 - max( 0.0, ((r1 < 1.0) ? r1 : 0.9999999) );
        float rnd2 = rand( vec2(mytrunc( uv.y, 40.0 * r1 ), time) );
        float r2 = sat( rnd2 );

        float rnd3 = rand( vec2(mytrunc( uv.y, 10.0*r0 ), time) );
        float r3 = (1.0-sat(rnd3+0.8)) - 0.1;

        float pxrnd = rand( uv + time );

        float ofs = 0.05 * r2 * GLITCH * ( rnd0 > 0.5 ? 1.0 : -1.0 );
        ofs += 0.5 * pxrnd * ofs;

        uv.y += 0.1 * r3 * GLITCH;

        const int NUM_SAMPLES = 20;
        const float RCP_NUM_SAMPLES_F = 1.0 / float(NUM_SAMPLES);

        vec4 sum = vec4(0.0);
        vec3 wsum = vec3(0.0);
        for( int i=0; i<NUM_SAMPLES; ++i )
        {
            float t = float(i) * RCP_NUM_SAMPLES_F;
            uv.x = sat( uv.x + ofs * t );
            vec4 child = texture2D(tex0, uv, -10.0);
            vec3 s = spectrum_offset( t );
            child.rgb = child.rgb * s;
            sum += child;
            wsum += s;
        }

        sum.rgb /= wsum;
        sum.a *= RCP_NUM_SAMPLES_F;

        gl_FragColor.a = sum.a;
        gl_FragColor.rgb = sum.rgb;
    """

    VHS_CRT_FUNCTIONS = """
        float sat( float t ) {
            return clamp( t, 0.0, 1.0 );
        }

        vec2 sat( vec2 t ) {
            return clamp( t, 0.0, 1.0 );
        }

        float remap  ( float t, float a, float b ) {
            return sat( (t - a) / (b - a) );
        }

        float linterp( float t ) {
            return sat( 1.0 - abs( 2.0*t - 1.0 ) );
        }

        vec3 spectrum_offset( float t ) {
            vec3 ret;
            float lo = step(t,0.5);
            float hi = 1.0-lo;
            float w = linterp( remap( t, 1.0/6.0, 5.0/6.0 ) );
            float neg_w = 1.0-w;
            ret = vec3(lo,1.0,hi) * vec3(neg_w, w, neg_w);
            return pow( ret, vec3(1.0/2.2) );
        }

        float rand( vec2 n ) {
            return fract(sin(dot(n.xy, vec2(12.9898, 78.233)))* 43758.5453);
        }

        float srand( vec2 n ) {
            return rand(n) * 2.0 - 1.0;
        }

        float mytrunc( float x, float num_levels )
        {
            return floor(x*num_levels) / num_levels;
        }
        vec2 mytrunc( vec2 x, float num_levels )
        {
            return floor(x*num_levels) / num_levels;
        }
    """


    HashBlur_SHADER_NAME = "V1FNaSR.HashBlur"

    HashBlur_VARIABLES = """
        uniform sampler2D tex0;
        uniform float u_time;
        uniform vec2 u_model_size;

        uniform float u_power;

        attribute vec2 a_tex_coord;

        varying vec2 v_tex_coord;
    """

    HashBlur_VERTEX_300 = """
        v_tex_coord = a_tex_coord;
    """

    HashBlur_FRAGMENT_300 = """
        vec2 bl_uv = v_tex_coord;
        
        float radius = pow(1.0 * (TAU * u_power), 2.0);

        float alpha = texture2D(tex0, bl_uv).a;
        
        gl_FragColor = vec4(Blur(bl_uv, radius, u_time, u_model_size, tex0), alpha);
    """

    HashBlur_FUNCTIONS = """
        #define ITERATIONS 20
        #define TAU 6.28318530718

        vec2 Sample(vec2 r) {
            r = fract(r * vec2(33.3983, 43.4427));
            return r-.5;
        }

        vec2 Hash22(vec2 p) {
            float HASHSCALE = 443.8975;

            vec3 p3 = fract(vec3(p.xyx) * HASHSCALE);
            p3 += dot(p3, p3.yzx+19.19);
            return fract(vec2((p3.x + p3.y)*p3.z, (p3.x+p3.z)*p3.y));
        }

        vec3 Blur(vec2 bl_uv, float radius, float time, vec2 model_size, sampler2D tex) {
            radius = radius * 0.04;
            
            vec2 circle = vec2(radius) * vec2((model_size.y / model_size.x), 1.0);
            
            vec2 random = Hash22(bl_uv + time);

            vec3 acc = vec3(0.0);
            for (int i = 0; i < ITERATIONS; i++)
            {
                acc += texture2D(tex, bl_uv + circle * Sample(random), radius * 10.0).xyz;
            }
            return acc / float(ITERATIONS);
        }

    """

    renpy.register_shader(HashBlur_SHADER_NAME,  variables=HashBlur_VARIABLES,  vertex_300=HashBlur_VERTEX_300,  fragment_300=HashBlur_FRAGMENT_300,  fragment_functions=HashBlur_FUNCTIONS)

    renpy.register_shader(VHS_CRT_SHADER_NAME,  variables=VHS_CRT_VARIABLES,  vertex_300=VHS_CRT_VERTEX_300,  fragment_300=VHS_CRT_FRAGMENT_300,  fragment_functions=VHS_CRT_FUNCTIONS)



    renpy.register_shader("v1_gradient_alpha_FNaSR",

        variables="""
            uniform float u_max_alpha;
            uniform float u_gradient_start;
            uniform float u_gradient_end;
        """,

        vertex_200="""
            v_tex_coord = a_tex_coord;
        """,

        fragment_200="""
            vec4 color = texture2D(tex0, v_tex_coord);

            float y = v_tex_coord.y;

            float gradient = smoothstep(u_gradient_end, u_gradient_start, y);

            color.a *= gradient * u_max_alpha;

            gl_FragColor = color;
        """
    )

init -20:
    transform v1_HashBlur_shader_t_FNaSR(power=0.125, update_rate=0.016):
        mesh True
        shader "V1FNaSR.HashBlur"

        u_power power

        pause update_rate
        repeat

    transform v1_vhs_crt_shader_t_FNaSR(glitch_power=0.01, glitch_speed=210.0, update_rate=0.016):
        mesh True
        shader "V1FNaSR.VHS_CRT"

        u_glitch_power glitch_power
        u_glitch_speed glitch_speed

        pause update_rate
        repeat

    transform v1_vhs_crt_shader_anim_t_FNaSR(glitch_power_start=0.75, glitch_power_end=0.015, glitch_speed=210.0, animation_time=0.5, update_time=0.016):
        mesh True
        shader "V1FNaSR.VHS_CRT"

        u_glitch_power glitch_power_start
        u_glitch_speed glitch_speed

        easein_quad animation_time u_glitch_power glitch_power_end

        block:
            shader "V1FNaSR.VHS_CRT"

            u_glitch_power glitch_power_end
            u_glitch_speed glitch_speed

            pause update_time
            repeat
    
    transform v1_vhs_crt_off_anim_t_FNaSR(glitch_power_start=0.015, glitch_power_end=0.0, glitch_speed=210.0, animation_time=0.5, update_time=0.016):
        mesh True
        shader "V1FNaSR.VHS_CRT"

        u_glitch_power glitch_power_start
        u_glitch_speed glitch_speed

        easein_quad animation_time u_glitch_power glitch_power_end

        block:
            shader None

    transform v1_gradient_transparent_FNaSR(max_alpha=1.0, start=1.0, end=0.0):
        shader "v1_gradient_alpha_FNaSR"

        u_max_alpha max_alpha
        u_gradient_start start
        u_gradient_end end
