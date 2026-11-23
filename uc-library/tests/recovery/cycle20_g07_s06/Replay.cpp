#include "presonus/panel/Page.hpp"

#include <cstdlib>
#include <iostream>

using Presonus::Panel::Element;
using Presonus::Panel::Page;

namespace {
class ObservedElement final : public Element {
public:
  ObservedElement(Page &page, int id) : page_(page), id_(id) {}

  void activate(int mode) override {
    if (observe)
      std::cout << id_ << ' ' << mode << ' '
                << (page_.selectedElement() == this ? id_ : 0) << ' ';
    Element::activate(mode);
  }

  bool observe = false;

private:
  Page &page_;
  int id_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int oldId = std::atoi(argv[1]), newId = std::atoi(argv[2]);
  if (oldId < 0 || oldId > 2 || newId < 0 || newId > 2)
    return 2;
  Page page;
  ObservedElement first(page, 1), second(page, 2);
  Element *elements[] = {nullptr, &first, &second};
  first.activate(1);
  second.activate(1);
  page.activeElement(elements[oldId]);
  first.setDirty(15);
  second.setDirty(15);
  first.observe = true;
  second.observe = true;
  page.activeElement(elements[newId]);
  const auto *active = page.selectedElement();
  std::cout << (active == &first    ? 1
                : active == &second ? 2
                                    : 0)
            << ' ' << first.elementState().dirty << ' '
            << first.elementState().activation << ' '
            << second.elementState().dirty << ' '
            << second.elementState().activation << '\n';
}
