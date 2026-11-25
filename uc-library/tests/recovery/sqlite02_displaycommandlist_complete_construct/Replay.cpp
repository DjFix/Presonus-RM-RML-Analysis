#include "core/portable/gui/corebitmap.h"
#include "presonus/DisplayCommandList.hpp"
#include <iomanip>
#include <iostream>

namespace {
using List = Presonus::DisplayCommandList;

using Subject = List;

// Explicit instantiation can name private members. Keep these observation
// hooks in the replay so production needs no test accessors or layout guesses.
struct StateMember {
  using Type = std::shared_ptr<List::State> List::*;
  friend Type observe(StateMember);
};
template <StateMember::Type member> struct ObserveState {
  friend StateMember::Type observe(StateMember) { return member; }
};
template struct ObserveState<&List::ownedState_>;

void printState(const List::State &state) {
  std::cout << state.count << ' ' << state.auxiliaryCursor << ' '
            << state.bitmapCount << ' ' << state.nextBitmapId;
  for (std::size_t i = 0; i < state.bitmapCount; ++i)
    std::cout << ' ' << state.bitmapEntries[i].key << ' '
              << state.bitmapEntries[i].id;
  std::cout << '\n';
}
} // namespace

int main() {
  Core::Rect rect;
  int red, green, blue, alpha;
  int x, y, srcX, srcY, width, height;
  if (!(std::cin >> rect.left >> rect.top >> rect.right >> rect.bottom >> red >>
        green >> blue >> alpha >> x >> y >> srcX >> srcY >> width >> height))
    return 1;
  const Core::Color color(red, green, blue, alpha);
  const Core::Portable::Bitmap bitmap;
  const auto key =
      static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(&bitmap));

  Subject first, second;
  const auto member = observe(StateMember{});
  const auto &firstState = first.*member;
  const auto &secondState = second.*member;
  if (!firstState || !secondState || firstState == secondState)
    return 2;
  std::cout << firstState->commands.size() << ' '
            << firstState->bitmapEntries.size() << ' ' << key << '\n';
  printState(*firstState);
  first.fillRect(rect, color);
  first.drawBitmap(x, y, bitmap, srcX, srcY, width, height);
  printState(*secondState);
  printState(*firstState);
  if (firstState->count < 0 ||
      static_cast<std::size_t>(firstState->count) > firstState->commands.size())
    return 3;
  std::cout << std::hex << std::setfill('0');
  for (int i = 0; i < firstState->count; ++i)
    for (auto byte : firstState->commands[i])
      std::cout << std::setw(2) << static_cast<unsigned>(byte);
  std::cout << '\n';

  List::State externalState;
  externalState.count = 1;
  externalState.auxiliaryCursor = 37;
  externalState.nextBitmapId = 42;
  List external(externalState);
  external.fillRect(rect, color);
  if (external.*member || externalState.count != 2 ||
      externalState.auxiliaryCursor != 37 || externalState.nextBitmapId != 42)
    return 4;
  return 0;
}
