#include "presonus/panel/LCDComponent.hpp"

#include <cstdint>

namespace Presonus::Panel {

void LCDComponent::setEditEncoder(Control *encoder) { editEncoder_ = encoder; }

Book *LCDComponent::getBook() const { return currentBook_; }

Book *LCDComponent::getBook(int tag) const {
  for (int index = 0; index < books_.count(); ++index) {
    auto *book = books_.at(index);
    if (book && book->getTag() == static_cast<std::uint32_t>(tag))
      return book;
  }
  return nullptr;
}

void LCDComponent::onIdle() { Component::onIdle(); }

void LCDComponent::doIdle() { onIdle(); }

Book *LCDComponent::createBook(int tag) const { return new Book(tag); }

} // namespace Presonus::Panel
