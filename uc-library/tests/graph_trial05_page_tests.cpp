#include "presonus/PageComponent.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <vector>

namespace {
struct Boundary final : presonus::page::Bindings {
  bool screen, current, editing;
  const void *page = nullptr;
  mutable std::vector<std::array<std::uint32_t, 3>> trace;
  Boundary(bool s, bool c, bool e) : screen(s), current(c), editing(e) {}
  void *castOwner(void *, int id) const override {
    trace.push_back({0x70000, 0x301000, static_cast<std::uint32_t>(id)});
    return screen ? reinterpret_cast<void *>(0x303000) : nullptr;
  }
  const void *currentPage(void *) const override {
    trace.push_back({0x734fc, 0x303000, 0});
    return current ? page : reinterpret_cast<void *>(0x304000);
  }
  void stopTextInput(void *, bool cancel) const override {
    trace.push_back({0x739e4, 0x303000, static_cast<std::uint32_t>(cancel)});
  }
  bool isEditingText(void *) const override {
    trace.push_back({0x73a04, 0x303000, 0});
    return editing;
  }
};
} // namespace
int main() {
  int n, owner, screen, current, editing, flag;
  std::uint32_t id;
  while (std::cin >> n >> owner >> screen >> current >> editing >> flag >> id) {
    Boundary b(screen, current, editing);
    Presonus::PageComponent p(
        owner ? reinterpret_cast<void *>(0x301000) : nullptr, b);
    b.page = &p;
    std::uint32_t result = 0;
    switch (n) {
    case 1: {
      void *cast = p.castTo(static_cast<std::int32_t>(id));
      if (cast && cast != &p)
        return 4;
      result = cast == &p ? 0x300000 : 0;
    } break;
    case 2:
      result = p.isVisible();
      break;
    case 3:
      result = static_cast<std::uint32_t>(
          reinterpret_cast<std::uintptr_t>(p.getMainScreen()));
      break;
    case 4:
      p.stopTextInput(flag);
      break;
    case 5:
      result = p.isEditingText();
      break;
    default:
      return 2;
    }
    std::cout << "{\"result\":" << result << ",\"trace\":[";
    for (std::size_t i = 0; i < b.trace.size(); ++i) {
      auto row = b.trace[i];
      if (i)
        std::cout << ',';
      std::cout << '[' << row[0] << ',' << row[1] << ',' << row[2] << ']';
    }
    std::cout << "]}\n";
  }
  return std::cin.eof() ? 0 : 3;
}
