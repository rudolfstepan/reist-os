#ifndef REIST_NATIVE_SURFACE_PLATFORM_H
#define REIST_NATIVE_SURFACE_PLATFORM_H
#include <x86os.h>
#include <reist/x86_64/syscall.h>
#include <reist/x86_64/graphical_session.h>
typedef struct {
    uint32_t endpoint,peer_generation,mode;
    uint64_t epoch,deadline,owner;
} reist_native_role_args;
/* Private receive history, no authority or client command. Fixed overwrite
 * storage permits read-only diagnostics without a stop per received event. */
typedef struct {
    uint64_t sequence,ms;
    uint32_t endpoint;
    unsigned char wire[140];
} reist_native_audit_entry;
typedef struct {
    uint64_t magic,owner,epoch,sequence;
    uint32_t version,capacity,bytes,exhausted;
    uint64_t reserved[2];
    reist_native_audit_entry entries[128];
} reist_native_audit_buffer;
_Static_assert(sizeof(reist_native_audit_entry)==160,"private receive entry");
_Static_assert(sizeof(reist_native_audit_buffer)==20544,"fixed private receive history");
extern volatile reist_native_audit_buffer reist_native_audit;
void reist_native_audit_init(uint64_t owner,uint64_t epoch);
void reist_native_audit_append(uint32_t,const x86os_ipc_message_t *,uint64_t ms);
void reist_native_zero(void *,size_t);
uint64_t reist_native_now(void);
int reist_native_sleep(unsigned);
int reist_native_role_arguments(int,char **,unsigned slot,reist_native_role_args *);
int reist_native_send(uint32_t,const void *,unsigned,unsigned);
int reist_native_receive(uint32_t,void *,unsigned,unsigned *length,unsigned);
int reist_native_control_send(uint32_t,const reist_graphical_control *);
int reist_native_control_valid(const reist_graphical_control *,unsigned type,
    unsigned role,uint64_t epoch,uint64_t owner,uint64_t sequence);
int reist_native_fault(unsigned mode);
int reist_native_fault_due(uint64_t now,uint64_t startup_deadline);
#endif
