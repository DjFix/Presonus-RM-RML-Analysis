#pragma once

#include "core/public/corevector.h"
#include "presonus/panel/Page.hpp"

#include <array>
#include <cstdint>
#include <memory>

namespace presonus::panel {
// Independent source-port adapter. Borrowed slot pointers refer to at least six
// readable bytes; this borrowed adapter and Books using it do not own slots or
// their pointees. This is not an assertion about the original Book fields or
// inheritance.
struct BorrowedBookState {
  Core::ConstVector<const unsigned char *> slots;
  BorrowedBookState(const unsigned char *const *items, int count)
      : slots(items, count) {}
};
} // namespace presonus::panel

namespace presonus::panel {
struct BookInspector;
}

namespace Presonus::Panel {
class Book {
public:
  explicit Book(int initialValue);
  explicit Book(const presonus::panel::BorrowedBookState &state)
      : borrowedState_(&state) {}
  // Portable copy preserves borrowed state and independent roster storage.
  // Copy operations throw std::logic_error if either Book owns a Page,
  // except for self-assignment.
  Book(const Book &other);
  Book &operator=(const Book &other);
  virtual ~Book();

  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }

  // The original return declarations remain unresolved. Raw registration
  // borrows the Page in this source port.
  void add(Page *page);
  Page *getActivePage() const;
  bool hasPage(const char *name) const;
  int previousPage();
  int nextPage();
  Core::Portable::Parameter *getActiveParam() const;
  virtual void switchToPage(int position);
  void switchToPage(const char *name);
  virtual bool canShowPage(int position) const;
  void makeValidPos();
  virtual void prepare();
  virtual void update(IDisplay &display);
  virtual void recall();
  virtual void store();
  virtual void next();
  virtual void previous();
  virtual void tap();
  void deltaEncoder(int delta);
  void pageup();
  void pagedown();
  void loadPreviousPage();

  // Portable ownership transfer. A full or inspection-only Book leaves the
  // supplied pointer with the caller.
  bool addOwnedPage(std::unique_ptr<Page> &page);
  // Portable choice: preserves the full observed zero-extended byte. The
  // original C++ return declaration remains unresolved; no ARM ABI claim.
  std::uint32_t isValidPos(int position);

  // The portable word type preserves all observed tag bits. The original
  // return declaration remains unresolved.
  std::uint32_t getTag() const;

  // Direct base entry. The original return declaration and polymorphic ABI
  // remain unresolved.
  void togglePage();

private:
  friend struct presonus::panel::BookInspector;
  // Independent source-port storage policy, not a recovered original layout.
  bool hasOwnedPages() const noexcept;
  static constexpr int maxPages = 32;
  Core::FixedSizeVector<Page *, maxPages> slots_;
  std::array<std::unique_ptr<Page>, maxPages> ownedPages_;
  const presonus::panel::BorrowedBookState *borrowedState_ = nullptr;
  int initialValue_ = 0;
  int activePosition_ = 0;
  std::uint32_t zeroState94_ = 0;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent inspection boundary for the bounded source-port state.
struct BookInspector {
  static int initialValue(const Presonus::Panel::Book &book) {
    return book.initialValue_;
  }
  static int count(const Presonus::Panel::Book &book) {
    return book.borrowedState_ ? book.borrowedState_->slots.count()
                               : book.slots_.count();
  }
  static bool ownsStorage(const Presonus::Panel::Book &book) {
    return !book.borrowedState_;
  }
  static const void *storage(const Presonus::Panel::Book &book) {
    return book.slots_.getItems();
  }
  static std::uint32_t zero90(const Presonus::Panel::Book &book) {
    return static_cast<std::uint32_t>(book.activePosition_);
  }
  static Presonus::Panel::Page *pageAt(const Presonus::Panel::Book &book,
                                       int position) {
    return book.slots_.isValidIndex(position) ? book.slots_.at(position)
                                              : nullptr;
  }
  static void setActivePosition(Presonus::Panel::Book &book, int position) {
    book.activePosition_ = position;
  }
  static void setPreviousPosition(Presonus::Panel::Book &book,
                                  unsigned int position) {
    book.zeroState94_ = position;
  }
  static std::uint32_t zero94(const Presonus::Panel::Book &book) {
    return book.zeroState94_;
  }
};
} // namespace presonus::panel
