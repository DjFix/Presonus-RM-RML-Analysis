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

class FixtureSender : public RemoteEventSender {
public:
  explicit FixtureSender(IConnection &connection)
      : RemoteEventSender(connection) {}
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  int destroyed = 0;
  EventFactory factory;
  BasicConnectionTypedValues values;
  BasicConnectionProviderScope providers(factory, values);
  BasicConnection first(2), second(2);
  BasicConnection &borrowed = std::atoi(argv[1]) == 0 ? first : second;
  BasicConnection &untouched = std::atoi(argv[1]) == 0 ? second : first;
  FixtureSender sender(borrowed);
  IEventHandler &dispatch = sender;
  auto *item = makeItem(destroyed, 99, 42);
  const auto ids = sender.sourcePortIDs();
  const int forwarded = dispatch.handleEvent(item, item->getData());
  const bool matched =
      !untouched.hasQueuedEvents() && borrowed.hasQueuedEvents() &&
      BasicConnectionSourceAccess::queue(borrowed).retrieveEvent() == item;
  if (!forwarded || !matched || item->getData().routeB != ids.remote ||
      destroyed)
    return 3;
  delete item;
  if (destroyed != 1)
    return 4;
  std::cout << ids.remote << ' ' << ids.local << ' ' << matched << '\n';
}
