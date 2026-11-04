#include "presonus/surface/NetworkSetupComponent.hpp"
#include <iostream>
int main() {
  Presonus::Surface::NetworkSetupComponent::ListModel model;
  for (int i = 0; i < 20; ++i) {
    auto *row = new Core::Portable::ListViewItem("row");
    row->setUserData(reinterpret_cast<void *>(static_cast<uintptr_t>(i + 1)));
    model.addItem(row);
  }
  Core::Portable::ListView a(Core::Rect(0, 0, 200, 60), &model);
  Core::Portable::ListView b(Core::Rect(0, 0, 200, 60), &model);
  model.setSelected(reinterpret_cast<Presonus::UC::NetworkItem *>(20));
  if (!model.isItemSelected(19) || model.isItemSelected(0) ||
      a.getScrollPosition() <= 0 || b.getScrollPosition() <= 0)
    return 1;
  model.setSelected(nullptr);
  if (!model.isItemSelected(0) || model.isItemSelected(19) ||
      a.getScrollPosition() != 0 || b.getScrollPosition() != 0)
    return 2;
  std::cout << "two actual CCL views: selection and scrolling passed\n";
}
