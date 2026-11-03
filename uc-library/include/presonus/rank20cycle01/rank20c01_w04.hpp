#pragma once
namespace presonus::surface {
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
  explicit DAWLoadDocumentPage(
      const presonus::surface::LoadDocumentBindings &bindings)
      : bindings_(bindings) {}
  bool onOk();

private:
  const presonus::surface::LoadDocumentBindings &bindings_;
};
} // namespace Presonus::Surface
