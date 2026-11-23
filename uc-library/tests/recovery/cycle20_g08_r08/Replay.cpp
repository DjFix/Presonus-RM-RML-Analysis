#include "presonus/panel/AlertBook.hpp"
#include "presonus/panel/Book.hpp"

#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>

namespace {

using Presonus::Panel::AlertBook;
using Presonus::Panel::Book;
using Presonus::Panel::Page;

void *receiver = nullptr;
std::array<int, 8> trace{};
std::size_t count = 0;
constexpr int component = -1;
constexpr int released = -2;

class ObservedPage final : public Page {
public:
  explicit ObservedPage(int index) : index_(index) {}
  ~ObservedPage() override { trace.at(count++) = index_; }

private:
  int index_;
};

class Observer final : public Core::Portable::ParamObserverBase {
public:
  void paramChanged(Core::Portable::Parameter *parameter,
                    int message) override {
    if (message == Core::Portable::Parameter::kDestroyed) {
      if (parameter->getTag() == 100)
        trace.at(count++) = component;
      ++destroyed;
      parameter->removeObserver(this);
    }
  }

  int destroyed = 0;
};

bool prepare(AlertBook &alert, Observer &observer, const std::string &roster) {
  auto *book = const_cast<Book *>(alert.portableOwnedBook());
  if (!book)
    return false;
  const auto &params = alert.portableParameters();
  if (params.countParameters() != 3)
    return false;
  for (int i = 0; i < 3; ++i) {
    auto *parameter = params.getParameterByTag(100 + i);
    if (!parameter)
      return false;
    parameter->addObserver(&observer);
  }
  for (int i = 0; i < static_cast<int>(roster.size()); ++i) {
    std::unique_ptr<Page> page;
    if (roster[i] == '1')
      page = std::make_unique<ObservedPage>(i);
    if ((roster[i] == '1' || roster[i] == '0') && !book->addOwnedPage(page))
      return false;
  }
  return true;
}

#if defined(__GNUC__)
__attribute__((noinline))
#endif
void deleteAlert(AlertBook *alert) {
  delete alert;
}
} // namespace

void *operator new(std::size_t size) {
  if (void *storage = std::malloc(size ? size : 1))
    return storage;
  throw std::bad_alloc();
}

void operator delete(void *storage) noexcept {
  if (storage && storage == receiver)
    trace.at(count++) = released;
  std::free(storage);
}

void operator delete(void *storage, std::size_t) noexcept {
  if (storage && storage == receiver)
    std::abort();
  std::free(storage);
}

int main() {
  std::string roster;
  bool deleting;
  while (std::cin >> deleting >> roster) {
    Observer observer;
    alignas(AlertBook) std::array<std::byte, sizeof(AlertBook)> storage{};
    auto *alert =
        deleting ? new AlertBook(41) : ::new (storage.data()) AlertBook(41);
    if (!prepare(*alert, observer, roster))
      return 1;
    receiver = alert;
    count = 0;
    if (deleting)
      deleteAlert(alert);
    else {
      alert->AlertBook::~AlertBook();
      storage.front() = std::byte{0x51};
    }
    receiver = nullptr;
    if (observer.destroyed != 3)
      return 1;
    for (std::size_t i = 0; i < count; ++i) {
      if (i != 0)
        std::cout << '|';
      if (trace[i] == component)
        std::cout << "component_d2";
      else if (trace[i] == released)
        std::cout << "receiver_delete";
      else
        std::cout << trace[i];
    }
    std::cout << '\n';
  }

  Core::Portable::Component borrowed("borrowed");
  {
    AlertBook alert(borrowed);
    if (alert.portableOwnedBook() || &alert.portableParameters() != &borrowed)
      return 1;
  }
  return std::string(borrowed.getName()) == "borrowed" ? 0 : 1;
}
