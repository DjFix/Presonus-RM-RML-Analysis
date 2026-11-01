"""Backend-independent SQLite closure; edge direction is dependent -> input."""


def impact(c, key, kinds):
    marks = ','.join('?' for _ in kinds)
    return c.execute(f'''WITH RECURSIVE affected(id) AS (
      SELECT ? UNION SELECT e.src FROM edges e JOIN affected a ON e.dst=a.id
      WHERE e.kind IN ({marks}))
      SELECT n.id,n.kind,n.label FROM affected a JOIN nodes n ON n.id=a.id
      ORDER BY n.kind,n.label''', (key, *kinds)).fetchall()


def impact_int(c, key, kinds):
    marks = ','.join('?' for _ in kinds)
    return c.execute(f'''WITH RECURSIVE affected(pk) AS (
      SELECT pk FROM nodes WHERE id=?
      UNION SELECT e.src FROM edges e JOIN affected a ON e.dst=a.pk
      WHERE e.kind IN ({marks}))
      SELECT n.id,n.kind,n.label FROM affected a JOIN nodes n ON n.pk=a.pk
      ORDER BY n.kind,n.label''', (key, *kinds)).fetchall()
