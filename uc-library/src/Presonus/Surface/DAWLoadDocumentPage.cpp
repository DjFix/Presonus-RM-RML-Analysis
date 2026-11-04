#include "presonus/surface/DAWLoadDocumentPage.hpp"
namespace Presonus::Surface {
bool DAWLoadDocumentPage::onOk() {
  void *document = bindings_.selectedDocument();
  if (!document)
    return false;
  bindings_.loadDocument(document);
  return true;
}
} // namespace Presonus::Surface
