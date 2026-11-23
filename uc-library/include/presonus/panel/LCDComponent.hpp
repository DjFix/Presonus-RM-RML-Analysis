#pragma once

#include "core/portable/corecomponent.h"
#include "presonus/panel/Book.hpp"

namespace Presonus::Panel {

class Control;

class LCDComponent : public Core::Portable::Component {
public:
  using Component::Component;
  using Books = Core::ConstVector<Book *>;

  // Portable bindings borrow the roster storage and each Book.
  void bindBooks(const Books &books) noexcept { books_ = books; }
  void bindCurrentBook(Book *book) noexcept { currentBook_ = book; }

  // The encoder is borrowed while bound.
  void setEditEncoder(Control *encoder);
  Control *editEncoder() const noexcept { return editEncoder_; }

  Book *getBook() const;
  Book *getBook(int tag) const;
  void onIdle() override;
  void doIdle();

  // Portable allocation transfers the returned Book to the caller.
  Book *createBook(int tag) const;

private:
  Books books_{nullptr, 0};
  Book *currentBook_ = nullptr;
  Control *editEncoder_ = nullptr;
};

} // namespace Presonus::Panel
