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
    Core::Vector<Presonus::UC::FileListReader::Entry> provider;
    for (unsigned i = 0; i < n; ++i) {
      Presonus::UC::FileListReader::Entry e{};
      e.size = i + 17;
      if (!v.add(e) || !provider.add(e))
        return 2;
    }
    Access::cursor(model) = cursor;
    // Observe actual pinned provider independently of the new app method.
    if (!provider.resize(0) || provider.count() || provider.getCapacity() ||
        provider.getItems())
      return 3;
    model.removeAll();
    if (v.getCapacity() || v.getItems() || v.count() != provider.count())
      return 4;
    std::cout << model.getItemCount() << ' ' << Access::cursor(model) << '\n';
    model.removeAll();
    if (model.getItemCount() || Access::cursor(model))
      return 5;
    Presonus::UC::FileListReader::Entry e{};
    if (!v.add(e) || model.getItemCount() != 1)
      return 6;
    model.removeAll();
    if (model.getItemCount() || v.getItems())
      return 7;
  }
}
