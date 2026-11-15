#pragma once
#include "core/public/corevector.h"
#include "presonus/uc/file_services.hpp"
#include <cstdint>
namespace presonus::surface {
struct LoadDocumentListStateAccess;
// Independent borrowed app boundary. No original class layout or ownership
// claim.
class LoadDocumentBindings {
public:
  virtual ~LoadDocumentBindings() = default;
  virtual void *selectedDocument() const = 0;
  virtual void loadDocument(void *) const = 0;
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Intentional portable composition; bool return is declaration-pending.
class DAWLoadDocumentPage {
public:
  // Bounded source-port model: one authoritative pinned-provider collection.
  // Native vector total is observed at +0x40 and a reset word at +0x4c;
  // these offsets do not establish host layout, inheritance or original types.
  // int/void return spellings remain original-declaration-pending.
  class ListModel {
  public:
    int getItemCount() const;
    void removeAll();

  private:
    Core::Vector<Presonus::UC::FileListReader::Entry> entries_;
    std::uint32_t cursor_ = 0;
    friend struct presonus::surface::LoadDocumentListStateAccess;
  };

  explicit DAWLoadDocumentPage(
      const presonus::surface::LoadDocumentBindings &bindings)
      : bindings_(bindings) {}
  bool onOk();

private:
  const presonus::surface::LoadDocumentBindings &bindings_;
};
} // namespace Presonus::Surface
