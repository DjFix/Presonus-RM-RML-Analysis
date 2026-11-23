#include "presonus/panel/AlertPage.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>

namespace {
void *receiver = nullptr;
std::array<int, 3> destroyed{};
int count = 0;
bool freed = false;

class ObservedElement final : public Presonus::Panel::Element {
public:
  explicit ObservedElement(int index) : index_(index) {}
  ~ObservedElement() override { destroyed[count++] = index_; }

private:
  int index_;
};
} // namespace

void *operator new(std::size_t size) {
  if (void *p = std::malloc(size ? size : 1))
    return p;
  throw std::bad_alloc();
}

void operator delete(void *memory) noexcept {
  if (memory && memory == receiver)
    freed = true;
  std::free(memory);
}

void operator delete(void *memory, std::size_t) noexcept {
  if (memory && memory == receiver)
    std::abort();
  std::free(memory);
}

int main() {
  std::string roster;
  while (std::cin >> roster) {
    Presonus::Panel::Page::Elements elements;
    for (int i = 0; i < static_cast<int>(roster.size()); ++i) {
      if (roster[i] == '0')
        elements.emplace_back();
      if (roster[i] == '1')
        elements.emplace_back(std::make_unique<ObservedElement>(i));
    }
    auto *page = new Presonus::Panel::AlertPage(std::move(elements));
    receiver = page;
    count = 0;
    freed = false;
    delete static_cast<Presonus::Panel::Page *>(page);
    receiver = nullptr;
    std::cout << freed;
    for (int i = 0; i < count; ++i)
      std::cout << '|' << destroyed[i];
    std::cout << '\n';
  }
}
