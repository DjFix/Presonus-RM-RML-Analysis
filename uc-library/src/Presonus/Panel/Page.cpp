#include "presonus/panel/Page.hpp"

#include "presonus/panel/FieldElement.hpp"
#include "presonus/panel/FillElement.hpp"
#include "presonus/panel/StaticElement.hpp"
#include <cstring>
#include <utility>

namespace Presonus::Panel {
Page::Page(Elements elements, std::string name)
    : elements_(std::move(elements)), name_(std::move(name)) {}

Page::Page(const char *name, const ElementInfo *infos, int count)
    : name_(std::string(name ? name : "").substr(0, 63)) {
  for (int index = 0; index < count; ++index) {
    const auto &info = infos[index];
    std::unique_ptr<Element> element;
    switch (info.word(0)) {
    case 0:
      if (std::strcmp(info.name(), "Link ID:") &&
          std::strcmp(info.name(), "Subgroup Merge:"))
        element = std::make_unique<StaticElement>(info);
      break;
    case 1:
      if (std::strcmp(info.name(), "global/link_id") &&
          std::strcmp(info.name(), "global/subgroupmerge"))
        element = std::make_unique<FieldElement>(info);
      break;
    case 2:
    case 3:
      element = std::make_unique<TextEntrySelection>(
          info, std::make_unique<TextEntryElement>(info));
      break;
    case 4:
      element = std::make_unique<FillElement>(info);
      break;
    default:
      break;
    }
    // Preserve the existing source-port ownership model, bounding the native
    // 32-slot roster. A rejected factory allocation is released in this port.
    if (element && elements_.size() < 32)
      elements_.push_back(std::move(element));
  }
}

bool Page::TextEntrySelection::editable() {
  if (ownedEntry_ && !sourceInfo().observation[92])
    return false;
  auto *parameter = entry_->getParam();
  return !parameter || parameter->isEnabled();
}
bool Page::TextEntrySelection::needsToDraw() const {
  return entry_->textState().dirty ||
         (entry_->fieldElement() && entry_->fieldElement()->needsToDraw());
}
void Page::TextEntrySelection::activate(int mode) {
  Element::activate(mode);
  if (auto *field = const_cast<FieldElement *>(entry_->fieldElement()))
    field->activate(mode);
}
void Page::TextEntrySelection::draw(IDisplay &display) {
  entry_->draw(display);
}
unsigned int Page::TextEntrySelection::next() { return entry_->next(); }
unsigned int Page::TextEntrySelection::previous() { return entry_->previous(); }
unsigned int Page::TextEntrySelection::tap() { return entry_->tap(); }
unsigned int Page::TextEntrySelection::deltaEncoder(int delta) {
  return entry_->deltaEncoder(delta);
}
void Page::TextEntrySelection::resetCursor() {
  // The accepted provider exposes its typed state as a const inspection view.
  // The entry itself is borrowed mutable (or owned mutable) here. Native Page
  // activation resets the cursor, not the encoder remainder.
  auto &state = const_cast<presonus::panel::portable::TextEntryState &>(
      entry_->textState());
  state.cursor = 0;
}

void Page::add(Element *element) {
  if (elements_.size() < 32)
    elements_.emplace_back(element);
}
Core::Portable::Parameter *Page::parameterOf(Element *element) {
  if (auto *typed = dynamic_cast<ParameterElement *>(element))
    return typed->parameter();
  if (auto *field = dynamic_cast<FieldElement *>(element))
    return field->getParam();
  return nullptr;
}
bool Page::setActiveParam(Core::Portable::Parameter *parameter) {
  for (auto &element : elements_) {
    if (!element->editable())
      continue;
    if (!parameterOf(element.get()))
      continue;
    auto *current = parameterOf(element.get());
    if (current && current == parameter) {
      activeElement(element.get());
      return true;
    }
  }
  return false;
}
bool Page::setActiveParam(unsigned int tag) {
  for (auto &element : elements_) {
    if (!element->editable())
      continue;
    if (!parameterOf(element.get()))
      continue;
    auto *current = parameterOf(element.get());
    if (current && current->getTag() == tag) {
      activeElement(element.get());
      return true;
    }
  }
  return false;
}
void Page::nextField() {
  bool passed = false;
  for (auto &element : elements_) {
    if (!element->editable())
      continue;
    if (!activeElement_) {
      activeElement(element.get());
      return;
    }
    if (element.get() == activeElement_) {
      if (element->next())
        return;
      passed = true;
    } else if (passed) {
      activeElement(element.get());
      return;
    }
  }
  for (auto &element : elements_)
    if (element->editable()) {
      activeElement(element.get());
      return;
    }
}
void Page::previousField() {
  bool passed = false;
  for (auto i = elements_.rbegin(); i != elements_.rend(); ++i) {
    auto *element = i->get();
    if (!element->editable())
      continue;
    if (!activeElement_) {
      activeElement(element);
      return;
    }
    if (element == activeElement_) {
      if (element->previous())
        return;
      passed = true;
    } else if (passed) {
      activeElement(element);
      return;
    }
  }
  for (auto i = elements_.rbegin(); i != elements_.rend(); ++i)
    if ((*i)->editable()) {
      activeElement(i->get());
      return;
    }
}
void Page::tap() {
  if (activeElement_)
    activeElement_->tap();
}
void Page::deltaEncoder(int delta) {
  if (activeElement_)
    activeElement_->deltaEncoder(delta);
}
void Page::activate(const char *previousPage) {
  previousPage_ = std::string(previousPage ? previousPage : "").substr(0, 63);
  for (auto &element : elements_)
    if (auto *text = dynamic_cast<TextEntrySelection *>(element.get()))
      text->resetCursor();
  if (!activeElement_)
    for (auto &element : elements_)
      if (element->editable()) {
        activeElement(element.get());
        break;
      }
  redraw_ = true;
}
void Page::updateParams() {
  for (auto &element : elements_) {
    if (auto *field = dynamic_cast<FieldElement *>(element.get()))
      field->setNeedsToDraw(true);
    if (auto *text = dynamic_cast<TextEntrySelection *>(element.get()))
      if (auto *field =
              const_cast<FieldElement *>(text->entry().fieldElement()))
        field->setNeedsToDraw(true);
  }
}
void Page::update(IDisplay &display) {
  if (redraw_) {
    redraw_ = false;
    display.clear();
    for (auto &element : elements_)
      element->draw(display);
  } else {
    for (auto &element : elements_)
      if (redraw_ || element->needsToDraw())
        element->draw(display);
  }
  display.update(false);
}

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
  return parameterOf(activeElement_);
}

void Page::deactivate() {}

void Page::recall() {}
void Page::store() {}
void Page::prepare() {}

const char *Page::getName() const { return name_.c_str(); }
} // namespace Presonus::Panel
