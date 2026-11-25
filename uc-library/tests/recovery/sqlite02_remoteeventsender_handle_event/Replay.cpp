#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/remote_event_sender.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <string_view>

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
void printHeader(const Event &header) {
  std::cout << header.type << ' ' << header.reserved04 << ' ' << header.routeA
            << ' ' << header.routeB;
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  int destroyed = 0;
  EventFactory factory;
  BasicConnectionTypedValues values;
  BasicConnectionProviderScope providers(factory, values);
  BasicConnection borrowed(2);
  RemoteEventSender sender(borrowed);
  IEventHandler &dispatch = sender;
  const std::string_view scenario(argv[1]);
  const auto route =
      static_cast<std::uint32_t>(std::strtoul(argv[2], nullptr, 10));
  sender.sourcePortIDs() = {route, 0x3456};

  if (scenario == "reject") {
    Event header{20566, 0x102938, 19, 0x88884444};
    const int result = dispatch.handleEvent(nullptr, header);
    if (borrowed.hasQueuedEvents() || destroyed)
      return 3;
    std::cout << result << ' ';
    printHeader(header);
    std::cout << " 0 0 0\n";
    return 0;
  }

  const bool coalesce = scenario == "coalesce";
  auto *prior = coalesce ? makeItem(destroyed, route, 11) : nullptr;
  if (prior && !borrowed.queueEvent(prior))
    return 4;
  auto *incoming = makeItem(destroyed, 0x88884444, 42);
  const int result = dispatch.handleEvent(incoming, incoming->getData());
  auto &queue = BasicConnectionSourceAccess::queue(borrowed);
  auto *survivor = queue.retrieveEvent();
  if (!survivor || queue.retrieveEvent() || destroyed != coalesce ||
      (coalesce ? survivor != prior : survivor != incoming))
    return 5;
  const auto *item = dynamic_cast<TrackedItem *>(survivor);
  if (!item || item->value.valueBits != 42)
    return 6;
  std::cout << result << ' ';
  printHeader(item->value.header);
  std::cout << ' ' << destroyed;
  delete item;
  std::cout << ' ' << destroyed << " 1\n";
}
