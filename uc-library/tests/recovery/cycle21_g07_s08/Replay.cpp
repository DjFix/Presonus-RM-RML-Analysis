#include "core/portable/gui/coreview.h"
#include "presonus/MainLCDComponent.hpp"

#include <cstdio>
#include <cstring>
#include <string>

using Core::Portable::ContainerView;
using Core::Portable::IViewOwner;
using Core::Portable::View;

namespace {
void append(std::string &trace, const char *name) {
  if (!trace.empty())
    trace += ',';
  trace += name;
}

struct Owner final : IViewOwner {
  std::string notifications;
  void viewDestroyed(View *view) override {
    append(notifications, view->getName());
  }
};

class TracedLeaf final : public View {
public:
  explicit TracedLeaf(std::string &calls) : calls_(calls) { setName("leaf"); }

  ContainerView *asContainer() override {
    append(calls_, getName());
    return View::asContainer();
  }

private:
  std::string &calls_;
};

class TracedContainer final : public ContainerView {
public:
  TracedContainer(std::string &calls, const char *name) : calls_(calls) {
    setName(name);
  }

  ContainerView *asContainer() override {
    append(calls_, getName());
    return ContainerView::asContainer();
  }

private:
  std::string &calls_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const bool nested = std::strcmp(argv[1], "1") == 0;
  const bool rootOwned = std::strcmp(argv[2], "1") == 0;
  Owner owner;
  std::string queries;
  {
    ContainerView root;
    root.setName("root");
    if (rootOwned)
      root.setOwner(&owner);
    if (nested) {
      auto *branch = new TracedContainer(queries, "branch");
      auto *tip = new TracedContainer(queries, "tip");
      branch->setOwner(&owner);
      tip->setOwner(&owner);
      branch->addView(tip);
      root.addView(new TracedLeaf(queries));
      root.addView(branch);
      Presonus::MainLCDComponent::prenotifyDestroy(&root);
      if (branch->getOwner() || tip->getOwner())
        return 3;
    } else {
      Presonus::MainLCDComponent::prenotifyDestroy(&root);
    }
    if (root.getOwner())
      return 3;
  }
  std::printf("%s\n%s\n", owner.notifications.c_str(), queries.c_str());
}
