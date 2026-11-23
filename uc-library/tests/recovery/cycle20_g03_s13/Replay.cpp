#include "presonus/MainLCDComponent.hpp"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/FaderUtilitiesPage.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

namespace {
class IdleApplication final : public presonus::mainlcd_port::Application {
public:
  Presonus::PageComponent *findPage(int) const override { std::abort(); }
  void requestPage(Presonus::PageComponent *) override { std::abort(); }
  void showNextPage() override { std::abort(); }
  int startPageTag() const override { std::abort(); }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    std::abort();
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
    std::abort();
  }
};

using Page = Presonus::Surface::FaderUtilitiesPage;

class Derived final : public Page {
public:
  using Page::Page;
};

struct Descriptor {
  const char *componentName;
  const char *form;
  int tag;
};

template <class P> bool check(const Descriptor &input, bool print) {
  P page(input.form, input.tag);
  const std::string_view name(page.getName());
  const std::string_view form(page.getFormName());
  if (name != input.componentName ||
      form != std::string_view(input.form).substr(0, 31) ||
      page.getPageTag() != input.tag || page.observedByte89() != 0 ||
      page.getParent() || page.getMainScreen() || page.isVisible() ||
      page.isEditingText())
    return false;
  page.stopTextInput(false);

  Core::Portable::Component unrelated;
  unrelated.addChild(&page);
  const bool rejected = page.getMainScreen() == nullptr && !page.isVisible();
  unrelated.removeChild(&page);

  IdleApplication application;
  presonus::mainlcd_port::State state;
  Presonus::MainLCDComponent owner(application, state);
  owner.addChild(&page);
  const bool attached = page.getParent() == &owner &&
                        page.getMainScreen() == &owner && !page.isVisible();
  state.current = &page;
  page.stopTextInput(true);
  const bool visible = page.isVisible() && !page.isEditingText();
  state.current = nullptr;
  owner.removeChild(&page);
  if (!rejected || !attached || !visible || page.getMainScreen() ||
      page.isVisible())
    return false;
  if (print)
    std::cout << name << '|' << form << '|' << page.getPageTag()
              << "|owner=attached\n";
  return true;
}

} // namespace

int main() {
  const Descriptor inputs[] = {
      {"faderUtilititesPage", "Form A", 17},
      {"faderUtilititesPage", "", 0},
      {"faderUtilititesPage", "01234567890123456789012345678901234", -1}};
  for (const Descriptor &input : inputs)
    if (!check<Page>(input, true) || !check<Derived>(input, false))
      return 1;
}
