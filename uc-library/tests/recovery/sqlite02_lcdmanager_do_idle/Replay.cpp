#include "presonus/panel/LCDManager.hpp"

#include <cassert>
#include <iostream>
#include <string_view>

using namespace Presonus::Panel;

namespace {
class Child final : public Core::Portable::Component {
public:
  void onIdle() override { ++idleCalls; }
  int idleCalls = 0;
};

class LookupOnly final : public ILCDDelegate {
public:
  Book *getDefaultBook() const override {
    ++bookCalls;
    return nullptr;
  }

  Core::Portable::Parameter *
  lookupElementParameter(const char *name) const override {
    ++lookupCalls;
    return std::string_view{name} == "level" ? &parameter : nullptr;
  }

  Core::Portable::ParamInfo info{};
  mutable Core::Portable::StringParam parameter{info};
  mutable int lookupCalls = 0;
  mutable int bookCalls = 0;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::string_view seed{argv[1]};
  LCDComponent lcd;
  auto *child = new Child;
  lcd.addChild(child);
  LookupOnly lookup;
  auto adapter =
      presonus::panel::portable::makeLCDComponentIdleDelegate(lcd, lookup);
  LCDManager manager{LCDManager::SourcePortConstruction{}};

  manager.setDelegate(&lookup);
  manager.doIdle();
  assert(child->idleCalls == 0);
  assert(lookup.lookupCalls == 0 && lookup.bookCalls == 0);

  if (seed == "unbound")
    manager.setDelegate(nullptr);
  else if (seed == "typed" || seed == "typed_twice")
    manager.setDelegate(&adapter);
  else
    return 2;
  manager.doIdle();
  if (seed == "typed_twice")
    manager.doIdle();

  assert(lookup.lookupCalls == 0 && lookup.bookCalls == 0);
  if (seed == "unbound") {
    assert(manager.lookupElementParameter("level") == nullptr);
    assert(manager.getDefaultBook() == nullptr);
  } else {
    assert(manager.lookupElementParameter("level") == &lookup.parameter);
    assert(manager.getDefaultBook() == nullptr);
    assert(lookup.lookupCalls == 1 && lookup.bookCalls == 1);
  }
  std::cout << "{\"idle_calls\":" << child->idleCalls << "}\n";
}
