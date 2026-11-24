#include "presonus/uc/event_factory.hpp"
#include "presonus/uc/event_queue.hpp"

#include <iostream>
#include <memory>

namespace {
class Item final : public Presonus::UC::EventItem {
public:
  Presonus::UC::Event &getData() override { return data_; }

private:
  Presonus::UC::Event data_{};
};

void *unusedValue(void *, const Presonus::UC::Event &,
                  presonus::uc::QueueValueKind) {
  return nullptr;
}
} // namespace

int main() {
  for (bool preexisting : {false, true}) {
    presonus::uc::OwnedEventQueueState storage(nullptr, unusedValue);
    Presonus::UC::EventQueue queue(storage);
    auto *previous = preexisting ? new Item : nullptr;
    if (previous)
      storage.append(previous);
    auto *added = new Item;
    queue.addEvent(added);
    std::cout << preexisting;
    while (auto *item = queue.retrieveEvent()) {
      std::cout << ' ' << (item == previous ? 1 : item == added ? 2 : -1);
      delete item;
    }
    std::cout << '\n';
  }
}
