import { Character } from '../../types'
import Card, { CardBody, CardFooter } from '../ui/Card'
import Button from '../ui/Button'

interface CharacterCardProps {
  character: Character
  onEdit: (character: Character) => void
  onDelete: (characterId: string) => void
}

export default function CharacterCard({
  character,
  onEdit,
  onDelete,
}: CharacterCardProps) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`"${character.name}" 캐릭터를 삭제하시겠습니까?`)) {
      onDelete(character.id)
    }
  }

  return (
    <Card hover onClick={() => onEdit(character)} className="h-full">
      <CardBody className="space-y-3">
        {/* 이름과 나이 */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {character.name}
          </h3>
          {character.age && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {character.age}세
            </p>
          )}
        </div>

        {/* 성격 특성 */}
        {character.personality_traits.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              성격 특성
            </p>
            <div className="flex flex-wrap gap-1">
              {character.personality_traits.slice(0, 3).map((trait, index) => (
                <span
                  key={index}
                  className="px-2 py-0.5 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded"
                >
                  {trait}
                </span>
              ))}
              {character.personality_traits.length > 3 && (
                <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded">
                  +{character.personality_traits.length - 3}
                </span>
              )}
            </div>
          </div>
        )}

        {/* 외모 요약 */}
        {character.appearance && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              외모
            </p>
            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
              {character.appearance}
            </p>
          </div>
        )}

        {/* 관계 */}
        {Object.keys(character.relationships).length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              관계
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              {Object.keys(character.relationships).length}개의 관계
            </p>
          </div>
        )}
      </CardBody>

      <CardFooter className="flex justify-end gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation()
            onEdit(character)
          }}
        >
          수정
        </Button>
        <Button size="sm" variant="danger" onClick={handleDelete}>
          삭제
        </Button>
      </CardFooter>
    </Card>
  )
}
