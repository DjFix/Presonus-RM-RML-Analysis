#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/remote_event_sender.hpp"
#include <array>
#include <cstdlib>
#include <iostream>

using namespace Presonus::UC;
using namespace presonus::uc;

namespace {
class TrackedItem final : public TypedEventItem<ParamValueEvent> {
public:
  explicit TrackedItem(int &destroyed) : destroyed_(destroyed) {}
  ~TrackedItem() override { ++destroyed_; }

private:
  int &destroyed_;
};

TrackedItem *makeItem(int &destroyed, std::uint32_t route,
                      std::uint32_t value) {
  auto *item = new TrackedItem(destroyed);
  item->value.header = {20566, 0x102938, 19, route};
  item->value.path[0] = 'a';
  item->value.index = 7;
  item->value.valueBits = value;
  return item;
}

void *watched = nullptr;
int releases = 0;
void noteRelease(void *pointer) {
  if (pointer == watched)
    ++releases;
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  noteRelease(pointer);
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  noteRelease(pointer);
  __real__ZdlPvm(pointer, size);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  int destroyed = 0;
  EventFactory factory;
  BasicConnectionTypedValues values;
  BasicConnectionProviderScope providers(factory, values);
  BasicConnection first(2), second(2);
  BasicConnection &borrowed = std::atoi(argv[1]) == 0 ? first : second;
  BasicConnection &untouched = std::atoi(argv[1]) == 0 ? second : first;
  auto *sender = new RemoteEventSender(borrowed);
  watched = sender;
  const auto seed = std::strtoul(argv[2], nullptr, 10);
  sender->sourcePortIDs() = {static_cast<std::uint32_t>(seed), 0x89FE};
  auto *prior = makeItem(destroyed, 19, 42);
  sender->handleEvent(prior, prior->getData());
  delete sender;
  watched = nullptr;
  auto *next = makeItem(destroyed, 123, 73);
  IConnection &typed = borrowed;
  if (!typed.queueEvent(next) || destroyed || untouched.hasQueuedEvents())
    return 3;
  auto &queue = BasicConnectionSourceAccess::queue(borrowed);
  bool preserved =
      queue.retrieveEvent() == prior && queue.retrieveEvent() == next;
  delete prior;
  delete next;
  if (!preserved || destroyed != 2)
    return 4;
  std::cout << releases << ' ' << preserved << '\n';
}
