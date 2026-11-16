#include "presonus/surface/CapturePageComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <new>
static void *watched;
static int releases;
static int children;
void operator delete(void *p) noexcept {
  if (p == watched)
    ++releases;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
struct Child : Core::Portable::Component {
  ~Child() override { ++::children; }
};
struct CaptureBoundary final : presonus::capture::Bindings {
  Core::Vector<void *> &
  observers(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  Core::Portable::Component *
  document(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  Core::Portable::Component *
  recordDiskSpace(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  Core::Portable::Component *
  session(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  Core::Portable::Component *
  arrangement(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  void *timeInfo(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  void *castTimeInfo(void *) const override { std::abort(); }
  bool progress(Presonus::DAWClientComponent *) const override { std::abort(); }
  void setDelegate(Presonus::DAWClientComponent *) const override {
    std::abort();
  }
  void baseOnShow(bool) const override { std::abort(); }
  void showStartPage(void *) const override { std::abort(); }
  void *modalPage(void *) const override { std::abort(); }
  void *castLoadPage(void *) const override { std::abort(); }
  void closeLoadPage(void *) const override { std::abort(); }
  void setTimeMode(void *, int) const override { std::abort(); }
  void setTimeFormat(void *, int) const override { std::abort(); }
  void wheel(void *, int) const override { std::abort(); }
  void *createDocumentPage(Presonus::DAWClientComponent *, const char *,
                           const char *) const override {
    std::abort();
  }
  void showModal(void *, void *) const override { std::abort(); }
  void command(Presonus::DAWClientComponent *, const char *,
               const char *) const override {
    std::abort();
  }
};
struct PageBoundary final : presonus::page::Bindings {
  void *castOwner(void *, int) const override { std::abort(); }
  const void *currentPage(void *) const override { std::abort(); }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};
int main() {
  CaptureBoundary bindings;
  PageBoundary pageBindings;
  Presonus::PageComponent page(nullptr, pageBindings);
  Core::Portable::Component parameters;
  for (int phase = 0; phase < 2; ++phase)
    for (int n = 0; n < 4; ++n) {
      children = 0;
      releases = 0;
      Core::Portable::Component *c =
          phase == 0 ? new Core::Portable::Component
                     : new Presonus::Surface::CapturePageComponent(
                           parameters, page, bindings);
      watched = c;
      for (int j = 0; j < n; ++j)
        c->addChild(new Child);
      Core::Portable::Component borrowed;
      c->addChild(&borrowed);
      c->removeChild(&borrowed);
      delete c;
      std::cout << n << " " << children << " " << releases << " "
                << (borrowed.getParent() == nullptr) << "\n";
      watched = nullptr;
    }
}
