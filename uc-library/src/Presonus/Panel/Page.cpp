#include "presonus/panel/Page.hpp"

#include <utility>

namespace Presonus::Panel {
Page::Page(Elements elements, std::string name)
    : elements_(std::move(elements)), name_(std::move(name)) {}

Page::~Page() {
  for (auto &element : elements_)
    element.reset();
}

void Page::activeElement(Element *element) {
  if (activeElement_ == element)
    return;
  if (activeElement_)
    activeElement_->activate(0);
  activeElement_ = element;
  if (activeElement_)
    activeElement_->activate(1);
}

Core::Portable::Parameter *Page::getActiveParam() const {
  const auto *parameterElement =
      dynamic_cast<const ParameterElement *>(activeElement_);
  return parameterElement ? parameterElement->parameter() : nullptr;
}

const char *Page::getName() const { return name_.c_str(); }
} // namespace Presonus::Panel
