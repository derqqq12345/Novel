import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { charactersApi } from '../../api'
import { Character, CharacterCreate, CharacterUpdate } from '../../types'
import CharacterCard from './CharacterCard'
import CharacterFormModal from './CharacterFormModal'
import Button from '../ui/Button'

interface CharacterListProps {
  projectId: string
  characters: Character[]
}

export default function CharacterList({
  projectId,
  characters,
}: CharacterListProps) {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(
    null
  )

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: CharacterCreate) =>
      charactersApi.create(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] })
      setIsModalOpen(false)
      setSelectedCharacter(null)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      characterId,
      data,
    }: {
      characterId: string
      data: CharacterUpdate
    }) => charactersApi.update(characterId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] })
      setIsModalOpen(false)
      setSelectedCharacter(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (characterId: string) => charactersApi.delete(characterId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] })
    },
  })

  // Handlers
  const handleAddCharacter = () => {
    setSelectedCharacter(null)
    setIsModalOpen(true)
  }

  const handleEditCharacter = (character: Character) => {
    setSelectedCharacter(character)
    setIsModalOpen(true)
  }

  const handleDeleteCharacter = (characterId: string) => {
    deleteMutation.mutate(characterId)
  }

  const handleSubmit = async (data: CharacterCreate | CharacterUpdate) => {
    if (selectedCharacter) {
      await updateMutation.mutateAsync({
        characterId: selectedCharacter.id,
        data,
      })
    } else {
      await createMutation.mutateAsync(data as CharacterCreate)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          캐릭터 ({characters.length})
        </h2>
        <Button size="sm" onClick={handleAddCharacter}>
          + 캐릭터 추가
        </Button>
      </div>

      {/* 캐릭터 그리드 */}
      {characters.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              아직 캐릭터가 없습니다
            </p>
            <Button onClick={handleAddCharacter}>첫 캐릭터 추가하기</Button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {characters.map((character) => (
              <CharacterCard
                key={character.id}
                character={character}
                onEdit={handleEditCharacter}
                onDelete={handleDeleteCharacter}
              />
            ))}
          </div>
        </div>
      )}

      {/* 캐릭터 폼 모달 */}
      <CharacterFormModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedCharacter(null)
        }}
        onSubmit={handleSubmit}
        character={selectedCharacter}
        existingCharacters={characters}
      />
    </div>
  )
}
