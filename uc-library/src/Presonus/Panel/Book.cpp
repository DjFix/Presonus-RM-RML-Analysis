#include "presonus/panel/Book.hpp"

#include "presonus/panel/key_input_provider.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <utility>

namespace Presonus::Panel {
Book::Book(int initialValue) : initialValue_(initialValue) {}

Book::Book(const Book &other) : Book(0) { *this = other; }

Book &Book::operator=(const Book &other) {
  if (this == &other)
    return *this;
  if (hasOwnedPages() || other.hasOwnedPages())
    throw std::logic_error("Cannot copy a Book with owned Pages");

  slots_ = other.slots_;
  borrowedState_ = other.borrowedState_;
  initialValue_ = other.initialValue_;
  activePosition_ = other.activePosition_;
  zeroState94_ = other.zeroState94_;
  return *this;
}

bool Book::hasOwnedPages() const noexcept {
  return std::any_of(ownedPages_.begin(), ownedPages_.end(),
                     [](const auto &page) { return static_cast<bool>(page); });
}

Book::~Book() {
  for (int index = 0; index < slots_.count(); ++index)
    ownedPages_[index].reset();
}

void Book::add(Page *page) {
  if (!borrowedState_)
    slots_.add(page);
}

bool Book::addOwnedPage(std::unique_ptr<Page> &page) {
  const int position = slots_.count();
  if (borrowedState_ || !slots_.add(page.get()))
    return false;
  ownedPages_[position] = std::move(page);
  return true;
}

Page *Book::getActivePage() const {
  if (activePosition_ >= slots_.count())
    return nullptr;
  return activePosition_ < 0 ? Core::ConstVector<Page *>::getError()
                             : slots_.at(activePosition_);
}

int Book::previousPage() {
  const int count =
      borrowedState_ ? borrowedState_->slots.count() : slots_.count();
  if (activePosition_ <= 0)
    return 0;
  for (int index = std::min(activePosition_, count) - 1; index >= 0; --index) {
    if (isValidPos(index))
      return index;
  }
  return 0;
}

int Book::nextPage() {
  const int count =
      borrowedState_ ? borrowedState_->slots.count() : slots_.count();
  if (activePosition_ >= count - 1)
    return 0;
  for (int index = std::max(activePosition_, -1) + 1; index < count; ++index) {
    if (isValidPos(index))
      return index;
  }
  return 0;
}

bool Book::hasPage(const char *name) const {
  const char *query = name ? name : "";
  for (int index = 0; index < slots_.count(); ++index) {
    const auto *page = slots_.at(index);
    if (!page)
      continue;
    const char *stored = page->getName();
    char truncated[64];
    const auto length = std::min(std::strlen(stored), sizeof(truncated) - 1);
    std::memcpy(truncated, stored, length);
    truncated[length] = '\0';
    if (std::strcmp(truncated, query) == 0)
      return true;
  }
  return false;
}

Core::Portable::Parameter *Book::getActiveParam() const {
  const auto *page = getActivePage();
  return page ? page->getActiveParam() : nullptr;
}

std::uint32_t Book::isValidPos(int position) {
  if (borrowedState_) {
    const auto &slots = borrowedState_->slots;
    if (!slots.isValidIndex(position))
      return 0;
    const auto *slot = slots.at(position);
    return slot ? slot[5] : 0;
  }
  if (!slots_.isValidIndex(position))
    return 0;
  const auto *page = slots_.at(position);
  return page && page->isEnabled();
}
std::uint32_t Book::getTag() const {
  return static_cast<std::uint32_t>(initialValue_);
}

bool Book::canShowPage(int position) const {
  if (!slots_.isValidIndex(position))
    return false;
  auto *page = slots_.at(position);
  // Null native receivers are excluded; the portable roster permits nulls.
  return page && page->isEnabled() &&
         (!page->requiresAltKey() ||
          KeyInputProvider::instance().altKeyPressed());
}
void Book::switchToPage(int position) {
  if (position == activePosition_ || !canShowPage(position))
    return;
  Page *previous = getActivePage();
  const int previousPosition = activePosition_;
  activePosition_ = std::clamp(position, 0, slots_.count() - 1);
  zeroState94_ = static_cast<std::uint32_t>(previousPosition);
  Page *next = getActivePage();
  if (previous != next && previous)
    previous->deactivate();
  if (previous && next)
    next->activate(previous->getName());
}
void Book::switchToPage(const char *name) {
  const char *query = name ? name : "";
  for (int i = 0; i < slots_.count(); ++i) {
    auto *page = slots_.at(i);
    if (page && std::strcmp(page->getName(), query) == 0) {
      switchToPage(i);
      return;
    }
  }
}
void Book::makeValidPos() {
  if (isValidPos(activePosition_))
    return;
  const int count =
      borrowedState_ ? borrowedState_->slots.count() : slots_.count();
  int i = activePosition_ <= 0 ? activePosition_ + 1 : activePosition_ - 1;
  for (; i < count; ++i)
    if (isValidPos(i)) {
      activePosition_ = i;
      return;
    }
  activePosition_ = 0;
}
void Book::prepare() { makeValidPos(); }
void Book::update(IDisplay &display) {
  if (auto *page = getActivePage())
    page->update(display);
}
void Book::recall() {
  if (auto *page = getActivePage())
    page->recall();
}
void Book::store() {
  if (auto *page = getActivePage())
    page->store();
}
void Book::next() {
  if (auto *page = getActivePage())
    page->nextField();
}
void Book::previous() {
  if (auto *page = getActivePage())
    page->previousField();
}
void Book::tap() {
  if (auto *page = getActivePage())
    page->tap();
}
void Book::deltaEncoder(int delta) {
  if (auto *page = getActivePage())
    page->deltaEncoder(delta);
}
void Book::pageup() { switchToPage(previousPage()); }
void Book::pagedown() { switchToPage(nextPage()); }
void Book::loadPreviousPage() { switchToPage(static_cast<int>(zeroState94_)); }

void Book::togglePage() {}

} // namespace Presonus::Panel
