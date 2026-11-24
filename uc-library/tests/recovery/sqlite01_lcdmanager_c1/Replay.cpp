#include "presonus/panel/LCDManager.hpp"

#include <iostream>
#include <string_view>
#include <type_traits>

using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::StringParam;
using Presonus::Panel::Book;
using Presonus::Panel::ILCDDelegate;
using Presonus::Panel::LCDManager;

namespace {
class Delegate final : public ILCDDelegate {
public:
  Book *getDefaultBook() const override {
    ++bookLookups;
    return &book;
  }

  Parameter *lookupElementParameter(const char *name) const override {
    ++parameterLookups;
    return name && std::string_view{name} == "panel/level" ? &parameter
                                                           : nullptr;
  }

  ParamInfo info{};
  mutable StringParam parameter{info};
  presonus::panel::BorrowedBookState state{nullptr, 0};
  mutable Book book{state};
  mutable unsigned bookLookups = 0;
  mutable unsigned parameterLookups = 0;
};

class DerivedManager final : public LCDManager {};

bool unbound(const LCDManager &manager) {
  return manager.getDefaultBook() == nullptr &&
         manager.lookupElementParameter("panel/level") == nullptr;
}

bool exercise(LCDManager &manager) {
  Delegate delegate;
  manager.setDelegate(&delegate);
  if (manager.getDefaultBook() != &delegate.book ||
      manager.lookupElementParameter("panel/level") != &delegate.parameter ||
      manager.lookupElementParameter("panel/unknown") != nullptr)
    return false;

  manager.setDelegate(nullptr);
  return unbound(manager) && delegate.bookLookups == 1 &&
         delegate.parameterLookups == 2;
}

template <class Manager> bool observe() {
  Manager manager;
  const bool hasBinding = !unbound(manager);
  if (!exercise(manager))
    return false;

  LCDManager tagged{LCDManager::SourcePortConstruction{}};
  if (!unbound(tagged) || !exercise(tagged))
    return false;

  std::cout << hasBinding << '\n';
  return true;
}
} // namespace

int main(int argc, char **argv) {
  static_assert(!std::is_polymorphic_v<LCDManager>);
  if (argc != 2)
    return 2;
  const std::string_view variant = argv[1];
  if (variant == "C1")
    return observe<LCDManager>() ? 0 : 1;
  if (variant == "C2")
    return observe<DerivedManager>() ? 0 : 1;
  return 2;
}
