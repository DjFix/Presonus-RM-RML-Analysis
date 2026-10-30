#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/no_member_events.hpp"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <pthread.h>
#include <stdexcept>
#include <string>
#include <type_traits>

using Presonus::UC::BasicConnection;
using Presonus::UC::EventItem;
using Access = presonus::uc::BasicConnectionSourceAccess;
extern "C" void ctor1(void *, int) asm("_ZN8Presonus2UC15BasicConnectionC1Ei");
extern "C" void ctor2(void *, int) asm("_ZN8Presonus2UC15BasicConnectionC2Ei");
extern "C" void dtor1(void *) asm("_ZN8Presonus2UC15BasicConnectionD1Ev");
extern "C" void dtor0(void *) asm("_ZN8Presonus2UC15BasicConnectionD0Ev");
namespace {
bool capture = false;
pthread_mutex_t *lastMutex = nullptr;
unsigned mutexInit = 0, mutexDestroy = 0;
void *target = nullptr;
void *itemPointers[8]{};
unsigned itemCount = 0;
char trace[4096]{};
unsigned used = 0;
void event(const char *text, int id = -1) {
  if (!capture)
    return;
  const int count =
      id < 0 ? std::snprintf(trace + used, sizeof(trace) - used, "%s,", text)
             : std::snprintf(trace + used, sizeof(trace) - used, "%s:%d,", text,
                             id);
  assert(count > 0 && unsigned(count) < sizeof(trace) - used);
  used += unsigned(count);
}
struct Item : presonus::uc::TypedEventItem<Presonus::UC::NoOpEvent> {
  int id;
  explicit Item(int id) : id(id) { value.header = {20047, 0, 0, 0}; }
  ~Item() override { event("item_dtor", id); }
};
void deleted(void *pointer) {
  if (!capture)
    return;
  if (pointer == target) {
    event("basic_delete");
    return;
  }
  for (unsigned i = 0; i < itemCount; ++i)
    if (pointer == itemPointers[i]) {
      event("item_delete", int(i));
      return;
    }
  // Source-port sidecar deallocation is real but intentionally not presented
  // as an original allocator event. Every delete below forwards its real call.
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *p) {
  deleted(p);
  __real__ZdlPv(p);
}
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  deleted(p);
  __real__ZdlPvm(p, n);
}
extern "C" int __real_pthread_mutex_init(pthread_mutex_t *,
                                         const pthread_mutexattr_t *);
extern "C" int __wrap_pthread_mutex_init(pthread_mutex_t *p,
                                         const pthread_mutexattr_t *attr) {
  const int code = __real_pthread_mutex_init(p, attr);
  assert(code == 0);
  lastMutex = p;
  ++mutexInit;
  return code;
}
extern "C" int __real_pthread_mutex_destroy(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_destroy(pthread_mutex_t *p) {
  const int code = __real_pthread_mutex_destroy(p);
  assert(code == 0);
  ++mutexDestroy;
  if (p == lastMutex)
    event("mutex_destroy");
  return code;
}
extern "C" int __real_pthread_mutex_lock(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_lock(pthread_mutex_t *p) {
  const int code = __real_pthread_mutex_lock(p);
  assert(code == 0);
  if (p == lastMutex)
    event("lock");
  return code;
}
extern "C" int __real_pthread_mutex_unlock(pthread_mutex_t *);
extern "C" int __wrap_pthread_mutex_unlock(pthread_mutex_t *p) {
  const int code = __real_pthread_mutex_unlock(p);
  assert(code == 0);
  if (p == lastMutex)
    event("unlock");
  return code;
}

int main(int argc, char **argv) {
  static_assert(std::is_base_of_v<Presonus::UC::IConnection, BasicConnection>);
  assert(argc >= 2);
  bool rejected = false;
  try {
    BasicConnection missing(0);
  } catch (const std::logic_error &) {
    rejected = true;
  }
  assert(rejected && mutexInit == 0);
  presonus::uc::CclFactoryRegistry registry(32);
  presonus::uc::ParamValueFactoryCodec valueCodec;
  presonus::uc::NoOpFactoryCodec noOpCodec;
  valueCodec.registerIn(registry.registry());
  noOpCodec.registerIn(registry.registry());
  Presonus::UC::EventFactory factory(registry.registry());
  presonus::uc::BasicConnectionTypedValues values;
  presonus::uc::BasicConnectionProviderScope providers(factory, values);
  if (std::strcmp(argv[1], "functional") == 0) {
    Presonus::UC::ParamValueEvent value{};
    value.header = {20566, 0, 1, 2};
    std::strcpy(value.path.data(), "/source/actual");
    value.valueBits = 0x3f800000;
    value.index = 4;
    auto binding = values.bind(value);
    valueCodec.bind(value);
    BasicConnection connection(7);
    auto &interface = static_cast<Presonus::UC::IConnection &>(connection);
    assert(dynamic_cast<BasicConnection *>(&interface) == &connection);
    assert(!connection.hasQueuedEvents());
    assert(interface.sendEvent(value.header) && connection.hasQueuedEvents());
    auto &state = Access::storage(connection);
    auto *first = state.items->getFirst();
    auto *typed = dynamic_cast<
        presonus::uc::TypedEventItem<Presonus::UC::ParamValueEvent> *>(first);
    assert(typed && !typed->getNext() &&
           typed->value.valueBits == value.valueBits);
    value.valueBits = 0x40000000;
    assert(interface.sendEvent(value.header));
    assert(state.items->getFirst() == first && !first->getNext());
    assert(typed->value.valueBits == value.valueBits);
    auto *incoming =
        new presonus::uc::TypedEventItem<Presonus::UC::ParamValueEvent>;
    incoming->value = value;
    incoming->value.valueBits = 0x40400000;
    assert(interface.queueEvent(static_cast<EventItem *>(incoming)));
    assert(state.items->getFirst() == first &&
           typed->value.valueBits == 0x40400000);
    assert(!interface.queueEvent(nullptr));
    Presonus::UC::Event absent{0x7fff, 0, 0, 0};
    assert(!interface.sendEvent(absent));
    Access::queue(connection).flush();
    assert(!connection.hasQueuedEvents());
    valueCodec.unbind(value);
    std::puts("PASS real_factory_clone=true actual_intrusive_coalescence=true "
              "genuine_IConnection=true missing_provider_rejected=true");
    return 0;
  }
  assert(argc == 9);
  const bool constructorTwo = std::atoi(argv[2]) == 2;
  const int type = int(std::strtoll(argv[3], nullptr, 10));
  const bool warm = std::atoi(argv[4]) != 0;
  const int count = std::atoi(argv[5]);
  const int ordering = std::atoi(argv[6]);
  const int fill = std::atoi(argv[7]);
  const bool deleting = std::atoi(argv[8]) != 0;
  assert(count >= 0 && count <= 5 && ordering >= 0 && ordering <= 2);
  if (warm)
    (void)presonus::uc::sourceActivitySingleton();
  const unsigned before = mutexInit;
  target = ::operator new(sizeof(BasicConnection));
  std::memset(target, fill, sizeof(BasicConnection));
  (constructorTwo ? ctor2 : ctor1)(target, type);
  auto *connection = static_cast<BasicConnection *>(target);
  assert(mutexInit - before == (warm ? 1U : 2U));
  assert(Access::connectionType(*connection) == type);
  assert(&Access::activity(*connection) ==
         &presonus::uc::sourceActivitySingleton());
  const auto &bytes = Access::activity(*connection).getActivityInfo().bytes;
  assert(bytes[0] == 136);
  for (unsigned i = 1; i < bytes.size(); ++i)
    assert(bytes[i] == 0);
  auto *iface = static_cast<Presonus::UC::IConnection *>(connection);
  assert(dynamic_cast<BasicConnection *>(iface) == connection);
  assert(!connection->hasQueuedEvents());
  int ids[8]{};
  for (int i = 0; i < count; ++i)
    ids[i] = ordering == 1   ? count - i - 1
             : ordering == 2 ? (i + 1) % count
                             : i;
  itemCount = unsigned(count);
  for (int i = 0; i < count; ++i) {
    auto *item = new Item(ids[i]);
    itemPointers[ids[i]] = item;
    Access::storage(*connection).append(item);
  }
  assert(connection->hasQueuedEvents() == (count != 0));
  const unsigned beforeDestroy = mutexDestroy;
  capture = true;
  (deleting ? dtor0 : dtor1)(connection);
  capture = false;
  assert(mutexDestroy == beforeDestroy + 1);
  if (!deleting)
    ::operator delete(target);
  std::printf("PASS type=%d ctor=%d warm=%d count=%d order=%d fill=%d "
              "deleting=%d trace=%s\n",
              type, constructorTwo ? 2 : 1, warm, count, ordering, fill,
              deleting, trace);
}
