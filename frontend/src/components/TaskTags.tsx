import type { TaskTag } from '../types'
import { tagTextColor } from '../tagColors'

export default function TaskTags({ tags = [] }: { tags?: TaskTag[] }) {
  return <span className="task-tags">{tags.map((tag, index) =>
    <span className="task-tag" key={index} style={{ backgroundColor: tag.color, color: tagTextColor(tag.color) }}>{tag.name}</span>
  )}</span>
}
