#include "presonus/surface/DAWLoadDocumentPage.hpp"
#include <cstdint>
#include <iostream>
namespace presonus::surface {
struct LoadDocumentListStateAccess {
  using Model = Presonus::Surface::DAWLoadDocumentPage::ListModel;
  static auto &entries(Model &m) { return m.entries_; }
  static auto &cursor(Model &m) { return m.cursor_; }
};
} // namespace presonus::surface
int main() {
  using Access = presonus::surface::LoadDocumentListStateAccess;
  unsigned n, cursor;
  while (std::cin >> n >> cursor) {
    Access::Model model;
    auto &v = Access::entries(model);
    for (unsigned i = 0; i < n; ++i) {
      Presonus::UC::FileListReader::Entry e{};
      e.size = i + 17;
      e.directory = (i % 2) != 0;
      if (!v.add(e))
        return 2;
    }
    Access::cursor(model) = cursor;
    const auto *oldItems = v.getItems();
    const int oldCapacity = v.getCapacity();
    const int result = model.getItemCount();
    if (oldItems != v.getItems() || oldCapacity != v.getCapacity())
      return 3;
    for (unsigned i = 0; i < n; ++i)
      if (v[i].size != i + 17 || v[i].directory != ((i % 2) != 0))
        return 4;
    std::cout << result << ' ' << v.count() << ' ' << Access::cursor(model)
              << '\n';
  }
}
