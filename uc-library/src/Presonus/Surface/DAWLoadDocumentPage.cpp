#include "presonus/surface/DAWLoadDocumentPage.hpp"
namespace Presonus::Surface {
int DAWLoadDocumentPage::ListModel::getItemCount() const {
  return entries_.count();
}
void DAWLoadDocumentPage::ListModel::removeAll() {
  entries_.resize(0);
  cursor_ = 0;
  entries_.empty();
}

bool DAWLoadDocumentPage::onOk() {
  void *document = bindings_.selectedDocument();
  if (!document)
    return false;
  bindings_.loadDocument(document);
  return true;
}
} // namespace Presonus::Surface
