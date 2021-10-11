{-# LANGUAGE RecordWildCards #-}

-- | A test module to load some fake data
module Monocle.Backend.Provisioner where

import Data.Time.Clock.System
import qualified Faker
import qualified Faker.Combinators
import qualified Faker.DateTime
import qualified Faker.Movie.BackToTheFuture
import qualified Faker.TvShow.Futurama
import Monocle.Api.Config (defaultTenant)
import Monocle.Backend.Documents
import qualified Monocle.Backend.Test as T
import Monocle.Env (testQueryM)
import Monocle.Prelude

-- | Provision fakedata for a tenant
runProvisioner :: Text -> IO ()
runProvisioner tenantName = do
  events <- createFakeEvents
  putTextLn $ "[provisioner] Adding " <> show (length events) <> " events to " <> tenantName <> "."
  testQueryM (defaultTenant tenantName) $ T.indexScenario events
  putTextLn $ "[provisioner] Done."

-- | Ensure changes have a unique ID
setChangeID :: [EChange] -> IO [EChange]
setChangeID xs = do
  -- create ids using epoch as a prefix
  MkSystemTime sec _ <- getSystemTime
  let mkid x = show sec <> show x
  let newChanges = zipWith (\c x -> c {echangeId = mkid x}) xs ([0 ..] :: [Int])
  pure $ map (\c -> c {echangeUrl = "http://review.example.org/" <> echangeId c}) newChanges

-- | Creates a bunch of event in the last 3 weeks
createFakeEvents :: IO [T.ScenarioEvent]
createFakeEvents = do
  now <- getCurrentTime
  from <- pure $ addUTCTime (-3600 * 24 * 7 * 3) now
  baseChanges <- Faker.generateNonDeterministic $ Faker.Combinators.listOf 10 $ fakeChange from now
  changes <- setChangeID baseChanges
  pure $ T.SChange <$> changes

fakeFileCount :: Faker.Fake Word32
fakeFileCount = Faker.Combinators.fromRange (0, 42)

fakeCommitCount :: Faker.Fake Word32
fakeCommitCount = Faker.Combinators.fromRange (1, 6)

fakeTitle :: Faker.Fake LText
fakeTitle = toLazy <$> Faker.Movie.BackToTheFuture.quotes

fakeAuthor :: Faker.Fake Author
fakeAuthor = do
  name <- toLazy <$> Faker.TvShow.Futurama.characters
  pure $ Author name name

fakeText :: Faker.Fake LText
fakeText = toLazy <$> Faker.TvShow.Futurama.quotes

fakeChange :: UTCTime -> UTCTime -> Faker.Fake EChange
fakeChange from to = do
  echangeId <- pure $ ""
  echangeType <- pure $ EChangeDoc
  echangeNumber <- pure $ 1
  echangeChangeId <- pure $ "change-id"
  echangeTitle <- fakeTitle
  echangeUrl <- pure $ ""
  echangeCommitCount <- fakeCommitCount
  echangeAdditions <- fakeFileCount
  echangeDeletions <- fakeFileCount
  echangeChangedFilesCount <- fakeFileCount
  echangeChangedFiles <- pure $ [File 0 0 "/fake/path"]
  echangeText <- fakeText
  echangeCommits <- pure $ []
  echangeRepositoryPrefix <- pure $ ""
  echangeRepositoryFullname <- pure $ ""
  echangeRepositoryShortname <- pure $ ""
  echangeAuthor <- fakeAuthor
  echangeBranch <- pure $ ""
  echangeCreatedAt <- dropTime <$> Faker.DateTime.utcBetween from to
  echangeUpdatedAt <- dropTime <$> Faker.DateTime.utcBetween echangeCreatedAt to
  echangeMergedBy <- pure $ Nothing
  echangeTargetBranch <- pure $ "main"
  echangeMergedAt <- pure $ Nothing
  echangeClosedAt <- pure $ Nothing
  echangeDuration <- pure $ Nothing
  echangeApproval <- pure $ Just ["OK"]
  echangeSelfMerged <- pure $ Nothing
  echangeTasksData <- pure $ Nothing
  echangeState <- pure $ EChangeOpen
  echangeMergeable <- Faker.Combinators.frequency [(5, pure "MERGEABLE"), (1, pure "")]
  echangeLabels <- pure $ []
  echangeAssignees <- pure $ []
  echangeDraft <- pure $ False
  pure $ EChange {..}

fakeChangeEvent :: UTCTime -> UTCTime -> Faker.Fake EChangeEvent
fakeChangeEvent from to = do
  echangeeventId <- pure ""
  echangeeventNumber <- pure 0
  echangeeventType <- Faker.Combinators.elements [minBound .. maxBound]
  echangeeventChangeId <- pure ""
  echangeeventUrl <- pure ""
  echangeeventChangedFiles <- pure []
  echangeeventRepositoryPrefix <- pure ""
  echangeeventRepositoryShortname <- pure ""
  echangeeventRepositoryFullname <- pure ""
  echangeeventAuthor <- pure Nothing
  echangeeventOnAuthor <- fakeAuthor
  echangeeventBranch <- pure ""
  echangeeventCreatedAt <- dropTime <$> Faker.DateTime.utcBetween from to
  echangeeventOnCreatedAt <- dropTime <$> Faker.DateTime.utcBetween echangeeventCreatedAt to
  echangeeventApproval <- pure Nothing
  echangeeventTasksData <- pure Nothing
  pure $ EChangeEvent {..}