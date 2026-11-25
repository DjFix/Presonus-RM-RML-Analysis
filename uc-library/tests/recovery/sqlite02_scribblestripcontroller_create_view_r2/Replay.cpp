#include "core/portable/corecomponent.h"
#include "presonus/MappingTable.hpp"
#include "presonus/McuVpotControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/ScribbleStripController.hpp"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using namespace Core::Portable;
using Item = Presonus::MappingTable::Item;
using PanelControl = Presonus::Panel::Control;
using Page = Presonus::IMainScreenPageController;

namespace {
constexpr ParamInfo aliasInfo = PARAM_ALIAS(1, "alias", 0);
constexpr ParamInfo rootInfo = PARAM_INT(2, "rootProbe", 0, 99, 1, 0, 0, 0, 0);

struct Root : Component, ComponentViewController<Root> {
  Root() { addParameters(&rootInfo, 1); }
  void *castTo(TypeID id) override {
    if (id == ViewController::kTypeID)
      return static_cast<ViewController *>(this);
    return Component::castTo(id);
  }
  void *getObjectForView(const char *name, const char *type) override {
    auto *result = ComponentViewController<Root>::getObjectForView(name, type);
    std::cout << "root\t" << name << '\t' << type << '\t'
              << (result == findParameter("rootProbe") ? 100 : 0) << '\n';
    return result;
  }
};

struct ObservedAlias : AliasParam {
  ObservedAlias() : AliasParam(aliasInfo) {}
  int observerCount() const { return observerList.count(); }
};

struct MappingOperations : presonus::mapping::ItemOperations,
                           presonus::mapping::ExtendedOperations {
  struct FixtureItem {
    std::string key;
    ObservedAlias alias;
    Item item{alias};
    explicit FixtureItem(const char *key) : key(key) {}
  };
  std::vector<std::unique_ptr<FixtureItem>> items;

  int identity(const Parameter *parameter) const {
    if (!parameter)
      return 0;
    for (std::size_t i = 0; i < items.size(); ++i)
      if (parameter == &items[i]->alias)
        return static_cast<int>(i) + 1;
    std::abort();
  }
  Parameter *parameter(Item &item) override {
    const int id = identity(item.alias);
    std::cout << "lookup\t" << items.at(id - 1)->key << '\t' << id << '\n';
    return item.alias;
  }
  void fullOff(Item &) override { std::abort(); }
  void inverseMode(Item &, bool) override { std::abort(); }
  void enabled(Item &, bool) override { std::abort(); }
  void immediate(Item &, bool) override { std::abort(); }
  void blink(Item &, const char *) override { std::abort(); }
  const char *pageName(Page &) override { std::abort(); }
  PanelControl *control(Item &) override { std::abort(); }
  void control(Item &, PanelControl *) override { std::abort(); }
  int translateMode(const char *) override { std::abort(); }
  void bind(PanelControl &, Parameter *, int) override { std::abort(); }
  Parameter *alternate(PanelControl &, bool) override { std::abort(); }
  void alternate(PanelControl &, Parameter *, bool) override { std::abort(); }
  bool hasLED(PanelControl &) override { std::abort(); }
  void color(PanelControl &, int) override { std::abort(); }
  const char *defaultColor(Item &) override { std::abort(); }
  void defaultColor(Item &, const char *) override { std::abort(); }
};

// These production objects are built with RTTI disabled. Compare their
// primary host vtable pointers before casting the view to the concrete type.
const void *vtable(const View &view) {
  const void *pointer;
  std::memcpy(&pointer, static_cast<const void *>(&view), sizeof(pointer));
  return pointer;
}

struct ChangedCounter : ParamObserverBase {
  int count = 0;
  void paramChanged(Parameter *, int message) override {
    if (message != Parameter::kChanged)
      std::abort();
    ++count;
  }
};

void replayView(View *view, const MappingOperations &ops) {
  std::unique_ptr<View> owned(view);
  if (!view) {
    std::cout << "result\t0\n";
    return;
  }
  const Core::Rect size = view->getSize();
  std::vector<ObservedAlias *> panParameters;
  Presonus::PanControl panReference(Core::Rect{}, nullptr);
  Presonus::McuVpotControl vpotReference(Core::Rect{}, nullptr);
  std::string kind;
  if (vtable(*view) == vtable(panReference)) {
    auto *pan = static_cast<Presonus::PanControl *>(view);
    kind = "pan";
    std::cout << "linked\t" << ops.identity(pan->panParameters()[1]) << '\n';
    std::cout << "number\t" << ops.identity(pan->panParameters()[2]) << '\n';
    for (auto *parameter : {pan->panParameters()[1], pan->panParameters()[2]})
      if (parameter && std::find(panParameters.begin(), panParameters.end(),
                                 parameter) == panParameters.end())
        panParameters.push_back(static_cast<ObservedAlias *>(parameter));
  } else if (vtable(*view) == vtable(vpotReference)) {
    auto state = static_cast<Presonus::McuVpotControl *>(view)->portableState();
    kind = "vpot";
    std::cout << "style\t" << ops.identity(state.styleParameter) << '\n';
    std::cout << "dot\t" << ops.identity(state.dotParameter) << '\n';
  } else {
    std::abort();
  }
  const auto *control = static_cast<Core::Portable::Control *>(view);
  std::cout << kind << '\t' << size.left << '\t' << size.top << '\t'
            << size.right << '\t' << size.bottom << '\t'
            << ops.identity(control->getParameter()) << '\n';
  ChangedCounter survived;
  for (auto *parameter : panParameters) {
    if (parameter->observerCount() != 1)
      std::abort();
    parameter->addObserver(&survived);
    parameter->changed();
  }
  if (survived.count != static_cast<int>(panParameters.size()))
    std::abort();
  owned.reset();
  for (auto *parameter : panParameters) {
    if (parameter->observerCount() != 1) {
      std::fputs("stale PanControl observer after virtual deletion\n", stderr);
      std::_Exit(4);
    }
    parameter->changed();
    parameter->removeObserver(&survived);
    if (parameter->observerCount() != 0)
      std::abort();
  }
  if (survived.count != 2 * static_cast<int>(panParameters.size()))
    std::abort();
  if (kind == "pan")
    std::cout << "post_delete_notifications\t" << panParameters.size() << '\n';
  std::cout << "result\tview\n";
}

const char *nullable(const char *argument) {
  return std::strcmp(argument, "<null>") == 0 ? nullptr : argument;
}
} // namespace

int main(int argc, char **argv) {
  if (argc < 5)
    return 2;
  MappingOperations ops;
  for (int i = 5; i < argc; ++i)
    ops.items.push_back(
        std::make_unique<MappingOperations::FixtureItem>(argv[i]));
  std::vector<presonus::mapping::Entry> entries;
  for (auto &item : ops.items)
    entries.push_back({item->key.c_str(), &item->item});
  std::sort(entries.begin(), entries.end(), [](const auto &a, const auto &b) {
    return std::strcmp(a.name, b.name) < 0;
  });
  Presonus::MappingTable mapping(entries.data(),
                                 static_cast<int>(entries.size()), ops);
  mapping.setExtendedOperations(ops);
  Root root;
  Presonus::Surface::ScribbleStripController controller(std::stoi(argv[2]),
                                                        mapping, root);
  ViewController *viewController = &controller;
  if (core_cast<ViewController>(viewController) != viewController)
    return 3;
  if (std::strcmp(argv[1], "create_view") == 0) {
    replayView(viewController->createView(nullable(argv[3])), ops);
  } else {
    auto *result =
        viewController->getObjectForView(nullable(argv[3]), nullable(argv[4]));
    std::cout << "result\t"
              << (result == root.findParameter("rootProbe")
                      ? 100
                      : ops.identity(static_cast<Parameter *>(result)))
              << '\n';
  }
}
