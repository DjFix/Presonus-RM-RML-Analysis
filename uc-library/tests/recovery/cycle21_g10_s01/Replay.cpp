#include "core/portable/gui/corebitmap.h"
#include "presonus/DisplayCommandList.hpp"
#include <algorithm>
#include <iomanip>
#include <iostream>

int main() {
  Core::Portable::Bitmap bitmap;
  const auto key =
      static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(&bitmap));
  Presonus::DisplayCommandList::State state;
  int x, y, srcX, srcY, width, height;
  if (!(std::cin >> state.count >> state.bitmapCount >> state.nextBitmapId >>
        x >> y >> srcX >> srcY >> width >> height) ||
      state.bitmapCount > state.bitmapEntries.size())
    return 1;
  for (std::size_t i = 0; i < state.bitmapCount; ++i) {
    std::int64_t offset;
    auto &entry = state.bitmapEntries[i];
    if (!(std::cin >> offset >> entry.id))
      return 1;
    entry.key = key + static_cast<std::uint32_t>(offset);
  }
  const auto end = state.bitmapEntries.begin() + state.bitmapCount;
  if (!std::is_sorted(
          state.bitmapEntries.begin(), end,
          [](const auto &a, const auto &b) { return a.key < b.key; }))
    return 2;
  for (auto &command : state.commands)
    command.fill(0xa5);

  Presonus::DisplayCommandList list(state);
  list.drawBitmap(x, y, bitmap, srcX, srcY, width, height);
  std::cout << key << ' ' << state.count << ' ' << state.bitmapCount << ' '
            << state.nextBitmapId << '\n';
  for (std::size_t i = 0; i < state.bitmapCount; ++i) {
    const auto &entry = state.bitmapEntries[i];
    std::cout << entry.key << ' ' << entry.id << '\n';
  }
  std::cout << std::hex << std::setfill('0');
  for (const auto &command : state.commands)
    for (auto byte : command)
      std::cout << std::setw(2) << static_cast<unsigned>(byte);
  std::cout << '\n';
}
