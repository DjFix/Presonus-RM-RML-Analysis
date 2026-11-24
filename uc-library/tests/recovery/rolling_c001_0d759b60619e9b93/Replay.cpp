#include "presonus/panel/Page.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <string_view>

using Presonus::Panel::Element;
using Presonus::Panel::Page;

namespace {
class RecordingElement final : public Element {
public:
  explicit RecordingElement(unsigned &callbacks) : callbacks_(callbacks) {}
  void activate(int mode) override {
    ++callbacks_;
    Element::activate(mode);
  }

private:
  unsigned &callbacks_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2 || argv[1][0] < '1' || argv[1][0] > '4' || argv[1][1] != '\0')
    return 2;

  const int scenario = argv[1][0] - '0';
  unsigned callbacks = 0;
  auto element = std::make_unique<RecordingElement>(callbacks);
  auto *observed = element.get();
  Page::Elements elements;
  elements.push_back(std::move(element));
  Page page(std::move(elements), "portable receiver");
  if (scenario % 2 == 0)
    page.activeElement(observed);

  const auto *selected = page.selectedElement();
  const auto before = observed->elementState();
  const auto callbacksBefore = callbacks;
  std::array<unsigned char, sizeof(Page)> pageBytes{};
  std::array<unsigned char, sizeof(RecordingElement)> elementBytes{};
  std::memcpy(pageBytes.data(), &page, pageBytes.size());
  std::memcpy(elementBytes.data(), observed, elementBytes.size());

  // Cover both a qualified call and the ordinary member-call expression.
  if (scenario <= 2)
    page.Page::prepare();
  else
    (page.*(&Page::prepare))();

  const auto &after = observed->elementState();
  const bool unchanged =
      std::memcmp(pageBytes.data(), &page, pageBytes.size()) == 0 &&
      std::memcmp(elementBytes.data(), observed, elementBytes.size()) == 0 &&
      page.selectedElement() == selected && page.isEnabled() &&
      std::string_view(page.getName()) == "portable receiver" &&
      before.x == after.x && before.y == after.y &&
      before.dirty == after.dirty && before.activation == after.activation;
  std::cout << unchanged << ' ' << callbacks - callbacksBefore << '\n';
}
