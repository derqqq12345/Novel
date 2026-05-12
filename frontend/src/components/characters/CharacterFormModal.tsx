import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Button from '../ui/Button'
import { Character, CharacterCreate, CharacterUpdate } from '../../types'

const characterSchema = z.object({
  name: z.string().min(1, '이름을 입력해주세요').max(200, '이름은 200자 이하여야 합니다'),
  age: z
    .number()
    .int('나이는 정수여야 합니다')
    .min(0, '나이는 0 이상이어야 합니다')
    .max(1000, '나이는 1000 이하여야 합니다')
    .nullable()
    .optional(),
  personality_traits: z.array(z.string()).optional(),
  appearance: z.string().max(2000, '외모 설명은 2000자 이하여야 합니다').optional(),
  background: z.string().max(5000, '배경 설명은 5000자 이하여야 합니다').optional(),
})

type CharacterFormData = z.infer<typeof characterSchema>

interface CharacterFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CharacterCreate | CharacterUpdate) => Promise<void>
  character?: Character | null
  existingCharacters?: Character[]
}

export default function CharacterFormModal({
  isOpen,
  onClose,
  onSubmit,
  character,
  existingCharacters = [],
}: CharacterFormModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [traitInput, setTraitInput] = useState('')
  const [traits, setTraits] = useState<string[]>([])
  const [relationships, setRelationships] = useState<Record<string, string>>({})

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<CharacterFormData>({
    resolver: zodResolver(characterSchema),
    defaultValues: {
      name: '',
      age: undefined,
      personality_traits: [],
      appearance: '',
      background: '',
    },
  })

  // 캐릭터 데이터 로드
  useEffect(() => {
    if (character) {
      reset({
        name: character.name,
        age: character.age ?? undefined,
        personality_traits: character.personality_traits,
        appearance: character.appearance ?? '',
        background: character.background ?? '',
      })
      setTraits(character.personality_traits || [])
      setRelationships(character.relationships || {})
    } else {
      reset({
        name: '',
        age: undefined,
        personality_traits: [],
        appearance: '',
        background: '',
      })
      setTraits([])
      setRelationships({})
    }
  }, [character, reset])

  const handleAddTrait = () => {
    const trimmed = traitInput.trim()
    if (trimmed && !traits.includes(trimmed)) {
      const newTraits = [...traits, trimmed]
      setTraits(newTraits)
      setValue('personality_traits', newTraits)
      setTraitInput('')
    }
  }

  const handleRemoveTrait = (index: number) => {
    const newTraits = traits.filter((_, i) => i !== index)
    setTraits(newTraits)
    setValue('personality_traits', newTraits)
  }

  const handleRelationshipChange = (characterId: string, relationship: string) => {
    setRelationships((prev) => ({
      ...prev,
      [characterId]: relationship,
    }))
  }

  const handleRemoveRelationship = (characterId: string) => {
    setRelationships((prev) => {
      const newRel = { ...prev }
      delete newRel[characterId]
      return newRel
    })
  }

  const onFormSubmit = async (data: CharacterFormData) => {
    setIsSubmitting(true)
    try {
      await onSubmit({
        ...data,
        age: data.age ?? undefined,
        personality_traits: traits,
        appearance: data.appearance || undefined,
        background: data.background || undefined,
        relationships,
      })
      onClose()
    } catch (error) {
      console.error('Failed to save character:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const availableCharacters = existingCharacters.filter(
    (c) => c.id !== character?.id
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={character ? '캐릭터 수정' : '새 캐릭터 추가'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
        {/* 이름 */}
        <Input
          label="이름 *"
          {...register('name')}
          error={errors.name?.message}
          placeholder="캐릭터 이름"
        />

        {/* 나이 */}
        <Input
          label="나이"
          type="number"
          {...register('age', {
            setValueAs: (v) => (v === '' || v === null ? undefined : parseInt(v)),
          })}
          error={errors.age?.message}
          placeholder="예: 25"
        />

        {/* 성격 특성 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            성격 특성
          </label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={traitInput}
              onChange={(e) => setTraitInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddTrait()
                }
              }}
              className="flex-1 px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              placeholder="예: 용감한, 정의로운"
            />
            <Button type="button" onClick={handleAddTrait} size="sm">
              추가
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {traits.map((trait, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1 px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-sm"
              >
                {trait}
                <button
                  type="button"
                  onClick={() => handleRemoveTrait(index)}
                  className="hover:text-primary-900 dark:hover:text-primary-100"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* 외모 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            외모
          </label>
          <textarea
            {...register('appearance')}
            rows={3}
            className="w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            placeholder="캐릭터의 외모를 설명해주세요"
          />
          {errors.appearance && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {errors.appearance.message}
            </p>
          )}
        </div>

        {/* 배경 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            배경
          </label>
          <textarea
            {...register('background')}
            rows={4}
            className="w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            placeholder="캐릭터의 배경 스토리를 입력해주세요"
          />
          {errors.background && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {errors.background.message}
            </p>
          )}
        </div>

        {/* 관계 설정 */}
        {availableCharacters.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              다른 캐릭터와의 관계
            </label>
            <div className="space-y-2">
              {availableCharacters.map((otherChar) => (
                <div key={otherChar.id} className="flex gap-2 items-center">
                  <span className="text-sm text-gray-700 dark:text-gray-300 w-32 flex-shrink-0">
                    {otherChar.name}
                  </span>
                  <input
                    type="text"
                    value={relationships[otherChar.id] || ''}
                    onChange={(e) =>
                      handleRelationshipChange(otherChar.id, e.target.value)
                    }
                    className="flex-1 px-3 py-1.5 text-sm border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    placeholder="예: 친구, 라이벌, 멘토"
                  />
                  {relationships[otherChar.id] && (
                    <button
                      type="button"
                      onClick={() => handleRemoveRelationship(otherChar.id)}
                      className="text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 버튼 */}
        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            {character ? '수정' : '추가'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
