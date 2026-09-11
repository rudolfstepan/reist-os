#include <reist_js_script.h>
#include <string.h>
#define SCHECK(x) do { if(!(x)) return __LINE__; } while(0)
static int js_script_vectors(int (*clock_fn)(void *,uint64_t *),void *opaque) {
    static char journal[REIST_JS_CONSOLE_BYTES],output[REIST_JS_RESULT_MAX];
    const char *args[]={"<eval>","'); throw 99; //","Gr\xc3\xbc\xc3\x9f"};
    for(unsigned mode=0;mode<21;++mode) {
        reist_js_config config={1,sizeof(config),32U*1024U*1024U,16384,
            REIST_JS_SOURCE_MAX,REIST_JS_RESULT_MAX,1024,0,42,opaque,clock_fn};
        reist_js_status status; reist_js_engine *engine=reist_js_create(&config,&status);
        SCHECK(engine && !status);
        uint64_t now; SCHECK(!clock_fn(opaque,&now)); size_t length=0;
        const char *absent="typeof print+','+typeof console+','+typeof scriptArgs+','+typeof reist";
        SCHECK(!reist_js_eval(engine,absent,strlen(absent),
            now+5000,output,sizeof(output),&length));
        SCHECK(!strcmp(output,"undefined,undefined,undefined,undefined"));
        reist_js_script_host host={1,sizeof(host),journal,sizeof(journal),0,0,0,0,0};
        SCHECK(!reist_js_script_attach(engine,&host,3,args));
        SCHECK(reist_js_script_attach(engine,&host,3,args)==REIST_JS_INVALID);
        const char *source=mode==0?"print(scriptArgs[1]);console.error(scriptArgs[2],42);reist.setExitCode(7);0":
            mode==1?"try{print('x'.repeat(61440))}catch(e){};42":
            mode==2?"for(let i=0;i<257;i++)print();0":
            mode==3?"try{print({toString(){print('nested');return 'outer'}})}catch(e){};0":
            mode==4?"print('before');throw Error('ordinary')":
            mode==5?"print({toString(){throw 3}})":
            mode==6?"reist.setExitCode(1.5)":
            mode==7?"reist.setExitCode('7')":
            mode==8?"print('x'.repeat(61431));0":
            mode==9?"console.log();Promise.resolve().then(()=>console.error('job'));0":
            mode==10?"[typeof os,typeof std,typeof process,typeof fetch,typeof Date,typeof SharedArrayBuffer].join(',')":
            mode==11?"reist.printColor('red','hello',42);reist.errorColor('bright-blue','err');print('plain');0":
            mode==12?"let n=0;for(const c of [undefined,null,1,{},new String('red'),'RED','red\\0','invalid']){try{reist.printColor(c,'bad')}catch(e){n++}};try{reist.errorColor()}catch(e){n++};if(n!==9)throw 1;0":
            mode==13?"try{reist.printColor('red',{toString(){reist.errorColor('blue','nested');return 'outer'}})}catch(e){};0":
            mode==14?"try{reist.printColor('red','x'.repeat(61428))}catch(e){};0":
            mode==15?"reist.printColor('red','x'.repeat(61427));0":
            mode==16?"reist.printColor('green','before');reist.printColor('red',{toString(){throw 3}})":
            mode==17?"let c=['black','red','green','yellow','blue','magenta','cyan','white'];for(let i=0;i<16;i++)reist.printColor((i<8?'':'bright-')+c[i%8],i);0":
            mode==18?"for(let i=0;i<257;i++)reist.errorColor('blue');0":
            mode==19?"try{print({toString(){reist.printColor('red','nested');return 'outer'}})}catch(e){};0":
            "try{reist.printColor('red',{toString(){try{print('nested')}catch(e){};return 'outer'}})}catch(e){};0";
        SCHECK(!clock_fn(opaque,&now));
        status=reist_js_eval(engine,source,strlen(source),now+5000,output,sizeof(output),&length);
        if((mode>=1 && mode<=3) || mode==13 || mode==14 || mode>=18) {
            SCHECK(status==REIST_JS_LIMIT && host.failed);
            SCHECK(reist_js_eval(engine,"1",1,now+5000,output,sizeof(output),&length)==REIST_JS_CLOSED);
        } else if((mode>=4 && mode<=7) || mode==16) {
            SCHECK(status==REIST_JS_EXCEPTION && !host.failed);
            SCHECK(host.records==(mode==4 || mode==16?1:0));
        } else {
            SCHECK(!status && !host.failed);
            if(mode==0) {
                uint32_t h[2]; memcpy(h,journal,8);
                SCHECK(host.records==2 && host.exit_code==7 && h[0]==1);
                SCHECK(h[1]==strlen(args[1])+1 && !memcmp(journal+8,args[1],strlen(args[1])));
                memcpy(h,journal+8+h[1],8); SCHECK(h[0]==2 && h[1]==10);
            }
            if(mode==8) SCHECK(host.records==1 && host.used==REIST_JS_CONSOLE_BYTES);
            if(mode==9) SCHECK(host.records==2);
            if(mode==10) SCHECK(!strcmp(output,"undefined,undefined,undefined,undefined,undefined,undefined"));
            if(mode==11) {
                uint32_t h[3];memcpy(h,journal,12);
                SCHECK(host.records==3 && h[0]==3 && h[1]==13 && h[2]==1);
                SCHECK(!memcmp(journal+12,"hello 42\n",9));
                memcpy(h,journal+21,12);SCHECK(h[0]==4 && h[1]==8 && h[2]==12);
                SCHECK(!memcmp(journal+33,"err\n",4));
                memcpy(h,journal+37,8);SCHECK(h[0]==1 && h[1]==6);
            }
            if(mode==12) SCHECK(!host.records && !host.used);
            if(mode==15) SCHECK(host.records==1 && host.used==REIST_JS_CONSOLE_BYTES);
            if(mode==17) {
                SCHECK(host.records==16);uint32_t at=0;
                for(uint32_t i=0;i<16;++i) {uint32_t h[3];memcpy(h,journal+at,12);
                    SCHECK(h[0]==3 && h[2]==i);at+=8+h[1];}
                SCHECK(at==host.used);
            }
        }
        reist_js_destroy(&engine); SCHECK(!engine);
    }
    return 0;
}
#undef SCHECK
