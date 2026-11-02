#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
#include <iostream>
#include <vector>

template <class T> T *ptr(unsigned value) {
  return reinterpret_cast<T *>(static_cast<std::uintptr_t>(value));
}
template <class T> unsigned token(T *p) {
  return static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(p));
}
template <class T, class F>
void removeCase(const std::vector<unsigned> &values, unsigned arg,
                unsigned sentinel, F f) {
  Core::Vector<T *> v;
  for (auto value : values)
    v.add(ptr<T>(value));
  Core::ConstVector<T *>::getError() = ptr<T>(sentinel);
  f(v, ptr<T>(arg));
  std::cout << v.count();
  for (unsigned i = 0; i < values.size(); ++i)
    std::cout << ' ' << token(v.getItems()[i]);
  std::cout << '\n';
  Core::ConstVector<T *>::getError() = nullptr;
}
int main() {
  int mode, n, arg;
  unsigned selected, sentinel;
  while (std::cin >> mode >> n >> arg >> selected >> sentinel) {
    std::vector<unsigned> values(n);
    for (auto &v : values)
      std::cin >> v;
    if (mode == 0) {
      Core::Vector<Presonus::AssignmentHandler *> v;
      for (auto value : values)
        v.add(ptr<Presonus::AssignmentHandler>(value));
      Core::ConstVector<Presonus::AssignmentHandler *>::getError() =
          ptr<Presonus::AssignmentHandler>(sentinel);
      Presonus::AssignmentHandlerTable table(v);
      std::cout << token(table.getHandler(arg)) << '\n';
      Core::ConstVector<Presonus::AssignmentHandler *>::getError() = nullptr;
    } else if (mode == 4) {
      removeCase<Presonus::AssignmentHandler>(
          values, arg, sentinel, [](auto &v, auto *p) {
            Presonus::AssignmentHandlerTable(v).removeHandler(p);
          });
    } else if (mode == 1 || mode == 2) {
      // Page objects retain the actual CCL storage; no production no-op
      // providers.
      auto pageCase = [&](auto &page) {
        auto &v = presonus::surface::PageObserverAccess::observers(page);
        using P = decltype(v.getError());
        (void)sizeof(P);
        using T = std::remove_pointer_t<std::remove_reference_t<P>>;
        for (auto value : values)
          v.add(ptr<T>(value));
        v.getError() = ptr<T>(sentinel);
        page.removeObserver(ptr<T>(arg));
        std::cout << v.count();
        for (unsigned i = 0; i < values.size(); ++i)
          std::cout << ' ' << token(v.getItems()[i]);
        std::cout << '\n';
        v.getError() = nullptr;
      };
      if (mode == 1) {
        Presonus::Surface::EQPageComponent page;
        pageCase(page);
      } else {
        Presonus::Surface::GeqPageComponent page;
        pageCase(page);
      }
    } else {
      Presonus::Surface::NetworkSetupComponent::ListModel model;
      for (auto value : values) {
        Core::Portable::ListViewItem *row = nullptr;
        if (value) {
          row = new Core::Portable::ListViewItem;
          row->setUserData(ptr<void>(value));
        }
        model.addItem(row);
      }
      Core::Portable::ListViewItem error;
      error.setUserData(ptr<void>(sentinel));
      Core::ConstVector<Core::Portable::ListViewItem *>::getError() =
          sentinel ? &error : nullptr;
      model.setSelectedItem(ptr<void>(selected));
      std::cout << model.isItemSelected(arg) << '\n';
      Core::ConstVector<Core::Portable::ListViewItem *>::getError() = nullptr;
    }
  }
}
